"""Command executor that interprets AI responses and executes actions."""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from loguru import logger

from .config import Config
from .ollama_client import OllamaClient
from .safety import SafetyManager, Operation, OperationType
from ..modules.app_control import AppController
from ..modules.file_operations import FileOperations
from ..modules.context_manager import ProjectContext
from ..modules.terminal_executor import TerminalExecutor
from ..modules.code_search import CodeSearch
from ..modules.git_integration import GitIntegration


class CommandExecutor:
    """Executes commands based on AI interpretation."""

    # System prompt for the AI
    SYSTEM_PROMPT = """You are PBOS AI, a concise, helpful assistant.

Respond ONLY with plain text answers to the user's message.
- Do NOT return JSON.
- Do NOT propose or perform actions.
- Do NOT open apps, URLs, or files.
- Keep responses clear, direct, and complete.
If the request is unclear, briefly ask for clarification in plain text."""

    # Cached prompt templates to avoid rebuilding each time
    PROMPT_TEMPLATE_BASE = (
        "\nDirectory: {cwd}\n"
        "Use simple filenames in this directory (no ../). "
        "Answer questions with the 'chat' action. "
        "Only run commands/open apps when the user clearly asks."
    )

    PROMPT_TEMPLATE_FOOTER = (
        "\nAct now: produce exactly one JSON action object per system prompt, "
        "wrapped in ```json``` with nothing else. Do not repeat or restate the task plan."
    )

    def __init__(
        self,
        config: Config,
        ollama_client: OllamaClient,
        safety_manager: SafetyManager
    ):
        """Initialize command executor.

        Args:
            config: Application configuration.
            ollama_client: Ollama client for AI interactions.
            safety_manager: Safety and permissions manager.
        """
        self.config = config
        self.ollama = ollama_client
        self.safety = safety_manager
        self.app_controller = AppController()
        self.file_ops = FileOperations()

        # Initialize new enhanced modules
        self.project_context = ProjectContext()
        self.terminal_executor = TerminalExecutor()
        self.code_search = CodeSearch()
        self.git = GitIntegration()

        # Track last user input for validation
        self.last_user_input = ""

        # Cache metrics
        self.parsing_stats = {"success": 0, "fallback": 0, "failed": 0}

        # Always run in chat-only passthrough mode
        self.chat_only_mode = True

        # Set system prompt
        self.ollama.set_system_prompt(self.SYSTEM_PROMPT)

    def update_ollama_client(self, ollama_client: OllamaClient) -> None:
        """Update the Ollama client reference while keeping executor state."""
        self.ollama = ollama_client
        self.ollama.set_system_prompt(self.SYSTEM_PROMPT)

    def execute_command(
        self,
        user_input: str,
        context: Optional[list[Dict[str, Any]]] = None,
        plan: Optional[Dict[str, Any]] = None
    ) -> str:
        """Execute a user command.

        Args:
            user_input: User's natural language command.
            context: Prior conversation for grounding.
            plan: Optional task plan for execution hints.

        Returns:
            Response message to display to user.
        """
        try:
            # Chat-only passthrough: send user text directly to model, return plain response.
            if getattr(self, "chat_only_mode", False):
                raw = self.ollama.chat(user_input, stream=False)
                return self._extract_plain_text(raw)

            # Store user input for validation
            self.last_user_input = user_input.lower()

            # Get AI response
            ai_response = self.ollama.chat(
                self._build_augmented_prompt(user_input, context, plan)
            )

            action_data = self._parse_ai_response(ai_response)

            if not action_data:
                # If parsing failed, return the AI response as-is
                return ai_response

            # If the user asked a question, force this to be a chat/clarify response.
            action_data = self._enforce_chat_for_questions(
                action_data,
                user_input,
                ai_response
            )

            # Execute the action
            result = self._execute_action(action_data)
            return result

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return f"Error: {str(e)}"

    def _build_augmented_prompt(
        self,
        user_input: str,
        context: Optional[List[Dict[str, Any]]],
        plan: Optional[Dict[str, Any]]
    ) -> str:
        """Attach light context/plan hints to the user input for the model."""
        cwd = Path.cwd()

        # Start with user input and cached base template
        parts = [
            user_input,
            self.PROMPT_TEMPLATE_BASE.format(cwd=cwd)
        ]

        # Add plan if available
        if plan:
            try:
                plan_preview = json.dumps(plan, ensure_ascii=True)
            except Exception:
                plan_preview = str(plan)
            parts.append(f"Current task plan: {plan_preview}")

        # Add context if available
        if context:
            # Respect configured memory while keeping prompt compact
            context_window = max(6, min(self.config.features.max_context_messages, 12))
            recent = context[-context_window:]
            context_lines = []
            for item in recent:
                role = item.get("role", "user")
                content = item.get("content", "")
                context_lines.append(f"{role}: {content}")
            parts.append("Recent context:\n" + "\n".join(context_lines))

        # Add cached footer template
        parts.append(self.PROMPT_TEMPLATE_FOOTER)

        return "\n\n".join(parts)

    def _parse_ai_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response to extract action data.

        Args:
            response: Raw AI response.

        Returns:
            Parsed action data or None if parsing failed.
        """
        parsing_method = None
        try:
            def _extract_first_json(text: str) -> Optional[Any]:
                """Try to grab the first JSON object from possibly noisy text."""
                decoder = json.JSONDecoder()

                # First try straight parsing
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass

                # Try newline-delimited JSON (common in streamed responses)
                for line in text.splitlines():
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        return json.loads(stripped)
                    except json.JSONDecodeError:
                        continue

                # Finally, try to decode the first object in the string
                stripped = text.lstrip()
                try:
                    obj, _ = decoder.raw_decode(stripped)
                    return obj
                except json.JSONDecodeError:
                    return None

            def _normalize_action(obj: Any) -> Optional[Dict[str, Any]]:
                """Normalize parsed JSON into a single action dict."""
                if isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, dict) and item:
                            return item
                    return None
                if isinstance(obj, dict):
                    return obj
                return None

            # Look for JSON in code blocks (prefer one containing an action)
            matches = list(re.finditer(r'```json\s*(.*?)\s*```', response, re.DOTALL))
            parsed_blocks: list[Dict[str, Any]] = []
            for match in matches:
                json_str = match.group(1)
                obj = _extract_first_json(json_str)
                normalized = _normalize_action(obj)
                if normalized:
                    parsed_blocks.append(normalized)

            # Prefer the first block that includes an action
            for block in parsed_blocks:
                if isinstance(block, dict) and "action" in block:
                    parsing_method = "json_code_block"
                    self.parsing_stats["success"] += 1
                    logger.debug(f"Parsing stats: {self.parsing_stats}")
                    return block

            # Fall back to the first parsed block (e.g., plan JSON without action)
            if parsed_blocks:
                parsing_method = "json_code_block_fallback"
                self.parsing_stats["fallback"] += 1
                logger.debug(f"Parsing stats: {self.parsing_stats}")
                return {
                    "action": "chat",
                    "parameters": {},
                    "explanation": response.strip()
                }

            # Try parsing the entire response as JSON
            obj = _extract_first_json(response)
            normalized = _normalize_action(obj)
            if normalized:
                if "action" in normalized:
                    parsing_method = "raw_json"
                    self.parsing_stats["success"] += 1
                    logger.debug(f"Parsing stats: {self.parsing_stats}")
                    return normalized
                parsing_method = "raw_json_fallback"
                self.parsing_stats["fallback"] += 1
                logger.debug(f"Parsing stats: {self.parsing_stats}")
                return {
                    "action": "chat",
                    "parameters": {},
                    "explanation": response.strip()
                }

            # As a last structured attempt, look for a loose JSON object containing "action"
            loose_match = re.search(r'\{[^{}]*"action"\s*:\s*"[^"]+"[^{}]*\}', response, re.DOTALL)
            if loose_match:
                try:
                    obj = json.loads(loose_match.group(0))
                    normalized = _normalize_action(obj)
                    if normalized:
                        parsing_method = "regex_action"
                        self.parsing_stats["success"] += 1
                        logger.debug(f"Parsing stats: {self.parsing_stats}")
                        return normalized
                except json.JSONDecodeError:
                    pass

            # Not structured JSON, treat as chat response
            parsing_method = "text_fallback"
            self.parsing_stats["fallback"] += 1
            logger.debug(f"Parsing stats: {self.parsing_stats}")
            return {
                "action": "chat",
                "parameters": {},
                "explanation": response.strip()
            }

        except Exception as e:
            self.parsing_stats["failed"] += 1
            logger.error(f"Failed to parse AI response: {e}. Parsing stats: {self.parsing_stats}")
            return None

    def _looks_like_question(self, user_input: str) -> bool:
        """Lightweight question detection to avoid accidental actions on questions."""
        text = user_input.lower().strip()
        if not text:
            return False
        question_starters = ("what", "why", "how", "when", "where", "who", "tell me", "explain", "could you", "would you", "can you", "help me")
        if text.endswith("?"):
            return True
        if text.startswith(question_starters):
            return True
        # Common patterns
        for phrase in ("how do i", "how to", "what is", "best way to", "give me", "walk me through", "outline", "steps", "guide", "instructions"):
            if phrase in text:
                return True
        return False

    def _enforce_chat_for_questions(
        self,
        action_data: Dict[str, Any],
        user_input: str,
        raw_response: str
    ) -> Dict[str, Any]:
        """Force chat/clarify for question-like prompts to prevent accidental actions."""
        if not self._looks_like_question(user_input):
            return action_data

        action = action_data.get("action")
        if action in {"chat", "clarify"}:
            return action_data

        # Convert to chat with the best available explanation
        explanation = action_data.get("explanation") or raw_response.strip()
        return {
            "action": "chat",
            "parameters": {},
            "explanation": explanation
        }

    def _validate_response_content(self, action: str, explanation: str) -> tuple[bool, str]:
        """Validate that a response has actual content.

        Args:
            action: The action type.
            explanation: The explanation text.

        Returns:
            Tuple of (is_valid, error_or_explanation).
        """
        # For chat actions, ensure there's actual content
        if action == "chat":
            # Only guard against truly empty output; be lenient for small models.
            if not explanation or len(explanation.strip()) < 4:
                return False, "I didn't catch an answer. Could you restate the question?"

        return True, explanation

    def _clean_explanation(self, explanation: str) -> str:
        """Remove action-like wording and return a text-only message."""
        if not explanation:
            return ""
        lower = explanation.lower()
        blocked_terms = ["opening", "open", "launching", "launch", "starting", "email client", "browser", "app", "application"]
        if any(term in lower for term in blocked_terms):
            return "Text-only mode: I won't open or launch anything. I'll stick to answering in text."
        return explanation

    def _extract_plain_text(self, raw: str) -> str:
        """If the model returns JSON, unwrap common fields to plain text."""
        try:
            obj = json.loads(raw)
            # If it's a list, take the first dict
            if isinstance(obj, list) and obj:
                obj = obj[0]
            if isinstance(obj, dict):
                for key in ("content", "explanation", "message", "text"):
                    if key in obj and isinstance(obj[key], str):
                        return obj[key]
                # Fallback: stringify dict
                return json.dumps(obj, ensure_ascii=False)
        except Exception:
            pass
        return raw

    def _execute_action(self, action_data: Dict[str, Any]) -> str:
        """Execute a specific action.

        Args:
            action_data: Parsed action data.

        Returns:
            Result message.
        """
        action = action_data.get("action")
        params = action_data.get("parameters", {})
        explanation = action_data.get("explanation", "")

        if action == "chat":
            explanation = self._clean_explanation(explanation) or explanation

        # Block app/URL/file launching actions entirely.
        disabled_actions = {"open_app", "close_app", "open_url", "open_file"}
        if action in disabled_actions:
            cleaned = self._clean_explanation(explanation)
            return cleaned or "Text-only mode: I won't open or close applications or URLs, but I can answer questions."

        # Final guard: if this looks like a question, treat anything non-chat/clarify as chat.
        if action not in {"chat", "clarify"} and self._looks_like_question(self.last_user_input):
            cleaned = self._clean_explanation(explanation)
            return cleaned or "Text-only mode: I'll answer your question directly."

        # Validate response content
        is_valid, result = self._validate_response_content(action, explanation)
        if not is_valid:
            return result

        # Handle chat action
        if action == "chat":
            return explanation

        # Create operation for safety check
        operation = self._create_operation(action, params)

        if not operation:
            if action == "clarify":
                question = explanation or params.get("question") or "Could you clarify?"
                return question
            # Fall back to returning the explanation as a normal chat response
            if explanation:
                return explanation
            if params.get("question"):
                return params["question"]
            return "I need a bit more detail to help. What exactly would you like?"

        # Check permissions
        permitted, reason = self.safety.check_permission(operation)
        if not permitted:
            return f"Permission denied: {reason}"

        # Check if confirmation needed
        if self.safety.requires_confirmation(operation):
            # In a real implementation, this would prompt the user
            # For now, we'll proceed
            logger.info(f"Confirmation would be required for: {action}")

        # Execute the action
        try:
            result = self._perform_action(action, params, operation)
            return f"{explanation}\n{result}"
        except KeyError as e:
            error_msg = f"Missing required parameter {str(e)} for action '{action}'. The AI model may be too small or not following the JSON format correctly."
            self.safety.log_operation(operation, False, error_msg)
            logger.error(f"Parameter error: {error_msg}")
            return f"Failed to {action}: {error_msg}"
        except Exception as e:
            self.safety.log_operation(operation, False, str(e))
            logger.error(f"Action execution error: {str(e)}")
            return f"Failed to {action}: {str(e)}"

    def _create_operation(
        self,
        action: str,
        params: Dict[str, Any]
    ) -> Optional[Operation]:
        """Create an operation object for safety checking.

        Args:
            action: Action type.
            params: Action parameters.

        Returns:
            Operation object or None if action is unknown.
        """
        action_map = {
            "create_file": (OperationType.FILE_CREATE, "file_path"),
            "append_file": (OperationType.FILE_APPEND, "file_path"),
            "read_file": (OperationType.FILE_READ, "file_path"),
            "modify_file": (OperationType.FILE_MODIFY, "file_path"),
            "delete_file": (OperationType.FILE_DELETE, "file_path"),
            "create_directory": (OperationType.DIR_CREATE, "dir_path"),
            "delete_directory": (OperationType.DIR_DELETE, "dir_path"),
            "list_directory": (OperationType.DIR_LIST, "dir_path"),
            "search_files": (OperationType.FILE_SEARCH, "directory"),
            "clarify": (OperationType.FILE_READ, "question"),  # benign placeholder
        }

        if action not in action_map:
            return None

        op_type, target_key = action_map[action]
        target = params.get(target_key, "unknown")

        return Operation(op_type, target, params)

    def _validate_file_path(self, file_path: str) -> tuple[bool, str]:
        """Validate a file path to ensure it's safe.

        Args:
            file_path: Path to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        # Check for parent directory references
        if ".." in file_path:
            return False, "File paths cannot contain '..' (parent directory references). Use simple filenames in the current directory."

        # Check for absolute paths outside current directory (on Unix)
        if file_path.startswith("/") and not str(Path.cwd()) in file_path:
            return False, "Absolute paths outside the current directory are not allowed. Use relative paths."

        return True, ""

    def _perform_action(
        self,
        action: str,
        params: Dict[str, Any],
        operation: Operation
    ) -> str:
        """Perform the actual action.

        Args:
            action: Action type.
            params: Action parameters.
            operation: Operation object for logging.

        Returns:
            Result message.
        """
        rollback_info = None

        # Validate file paths for file operations
        file_path_params = ["file_path", "dir_path"]
        for param_name in file_path_params:
            if param_name in params:
                is_valid, error_msg = self._validate_file_path(params[param_name])
                if not is_valid:
                    return error_msg

        try:
            if action == "open_app":
                success, message = self.app_controller.open_application(
                    params["app_name"]
                )

            elif action == "close_app":
                success, message = self.app_controller.close_application(
                    params["app_name"],
                    params.get("force", False)
                )

            elif action == "create_file":
                success, message, rollback_info = self.file_ops.create_file(
                    params["file_path"],
                    params.get("content", "")
                )

            elif action == "read_file":
                success, message, content = self.file_ops.read_file(
                    params["file_path"]
                )
                if success and content:
                    message = f"File content:\n{content}"

            elif action == "modify_file":
                success, message, rollback_info = self.file_ops.modify_file(
                    params["file_path"],
                    params["content"]
                )

            elif action == "append_file":
                success, message, rollback_info = self.file_ops.append_file(
                    params["file_path"],
                    params.get("content", "")
                )

            elif action == "delete_file":
                success, message, rollback_info = self.file_ops.delete_file(
                    params["file_path"]
                )

            elif action == "open_file":
                success, message = self.app_controller.open_file_with_default_app(
                    params["file_path"]
                )

            elif action == "create_directory":
                success, message = self.file_ops.create_directory(
                    params["dir_path"]
                )

            elif action == "delete_directory":
                success, message = self.file_ops.delete_directory(
                    params["dir_path"],
                    params.get("recursive", False)
                )

            elif action == "list_directory":
                success, message, contents = self.file_ops.list_directory(
                    params.get("dir_path", ".")
                )
                if success and contents:
                    formatted = "\n".join([
                        f"[{'DIR' if c['type'] == 'directory' else 'FILE'}] {c['name']}"
                        for c in contents
                    ])
                    message = f"Directory contents:\n{formatted}"

            elif action == "search_files":
                success, message, matches = self.file_ops.search_files(
                    params.get("directory", params.get("dir_path", ".")),
                    params.get("pattern", "*")
                )
                if success and matches:
                    message = f"Found files:\n" + "\n".join(matches)

            elif action == "open_url":
                # Validate that user explicitly asked to open a URL
                url_keywords = ["open", "browse", "go to", "visit", "show me", "navigate to"]
                user_wants_url = any(keyword in self.last_user_input for keyword in url_keywords)

                if not user_wants_url:
                    # User didn't ask to open a URL, they asked a question
                    return (
                        "I should answer your question directly instead of opening a browser. "
                        "Please ask me again and I'll provide a proper answer. "
                        "(If you specifically want me to open a website, use words like 'open', 'browse to', or 'visit')"
                    )

                success, message = self.app_controller.open_url(params["url"])

            # New enhanced actions
            elif action == "run_command":
                result = self.terminal_executor.execute(params["command"])
                success = result.success
                if result.stdout:
                    message = f"Command output:\n{result.stdout}"
                elif result.stderr:
                    message = f"Command error:\n{result.stderr}"
                else:
                    message = "Command executed successfully (no output)"

            elif action == "run_tests":
                result = self.terminal_executor.run_tests(params.get("test_command"))
                success = result.success
                message = f"Tests {'passed' if success else 'failed'}:\n{result.stdout}\n{result.stderr}"

            elif action == "run_build":
                result = self.terminal_executor.run_build(params.get("build_command"))
                success = result.success
                message = f"Build {'succeeded' if success else 'failed'}:\n{result.stdout}\n{result.stderr}"

            elif action == "search_code":
                matches = self.code_search.grep(
                    params["pattern"],
                    file_pattern=params.get("file_pattern", "*"),
                    context_lines=params.get("context_lines", 2),
                    max_results=params.get("max_results", 20)
                )
                success = True
                if matches:
                    formatted = []
                    for match in matches:
                        formatted.append(f"{match.file_path}:{match.line_number}: {match.line_content}")
                    message = f"Found {len(matches)} matches:\n" + "\n".join(formatted[:20])
                else:
                    message = "No matches found"

            elif action == "find_definition":
                definitions = self.code_search.find_definition(
                    params["name"],
                    def_type=params.get("type")
                )
                success = True
                if definitions:
                    formatted = []
                    for defn in definitions:
                        formatted.append(f"{defn.file_path}:{defn.line_number} - {defn.type} {defn.name}")
                        if defn.signature:
                            formatted.append(f"  {defn.signature}")
                    message = f"Found {len(definitions)} definition(s):\n" + "\n".join(formatted)
                else:
                    message = f"No definition found for '{params['name']}'"

            elif action == "get_project_summary":
                if not self.project_context._initialized:
                    self.project_context.initialize()
                summary = self.project_context.get_project_summary()
                success = True
                message = f"Project Summary:\n{summary}"

            elif action == "git_status":
                status = self.git.get_status()
                success = status is not None
                if status:
                    lines = [
                        f"Branch: {status.branch}",
                        f"Staged files: {len(status.staged)}",
                        f"Unstaged files: {len(status.unstaged)}",
                        f"Untracked files: {len(status.untracked)}",
                    ]
                    if status.staged:
                        lines.append("\nStaged:")
                        lines.extend([f"  - {f}" for f in status.staged[:10]])
                    if status.unstaged:
                        lines.append("\nUnstaged:")
                        lines.extend([f"  - {f}" for f in status.unstaged[:10]])
                    message = "\n".join(lines)
                else:
                    message = "Not a git repository"

            elif action == "git_diff":
                diff = self.git.get_diff(staged=params.get("staged", False))
                success = True
                if diff:
                    message = f"Git diff:\n{diff[:2000]}"  # Limit to 2000 chars
                else:
                    message = "No changes to show"

            elif action == "git_commit":
                success, msg = self.git.commit(params["message"])
                message = msg

            elif action == "analyze_file":
                file_path = Path(params["file_path"])
                if file_path.suffix == '.py':
                    analysis = self.project_context.analyze_python_file(file_path)
                    success = True
                    lines = [f"Analysis of {file_path.name}:"]
                    if analysis.get('docstring'):
                        lines.append(f"\nDocstring: {analysis['docstring']}")
                    if analysis.get('classes'):
                        lines.append(f"\nClasses ({len(analysis['classes'])}):")
                        for cls in analysis['classes'][:5]:
                            lines.append(f"  - {cls['name']} (line {cls['line']})")
                    if analysis.get('functions'):
                        lines.append(f"\nFunctions ({len(analysis['functions'])}):")
                        for func in analysis['functions'][:5]:
                            lines.append(f"  - {func['name']} (line {func['line']})")
                    message = "\n".join(lines)
                else:
                    success = False
                    message = f"File analysis not supported for {file_path.suffix} files yet"

            else:
                success = False
                message = f"Unknown action: {action}"

            # Log the operation
            self.safety.log_operation(operation, success)

            # Record for rollback if applicable
            if success and rollback_info:
                self.safety.record_for_rollback(operation, rollback_info)

            return message

        except Exception as e:
            self.safety.log_operation(operation, False, str(e))
            raise
