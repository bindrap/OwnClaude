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


class CommandExecutor:
    """Executes commands based on AI interpretation."""

    # System prompt for the AI
    SYSTEM_PROMPT = """You are OwnClaude, a helpful AI assistant that helps users control their computer through natural language commands.

Your role is to understand user requests and respond with exactly one structured action. You can:
1. Open and close applications
2. Create, read, modify, append, and delete files (and directories)
3. Open documents/paths with the default application
4. Search for files and list directories
5. Open URLs in browsers
6. Answer questions and provide information
7. Ask a quick clarifying question when needed (use the \"clarify\" action)

When a user asks you to perform an action, respond with a single JSON object in this format. Do not include multiple JSON objects or any text outside the code block.

{
    "action": "action_type",
    "parameters": {
        "param1": "value1",
        "param2": "value2"
    },
    "explanation": "Brief explanation of what you're doing"
}

Available actions:
- "open_app": Open an application (params: app_name)
- "close_app": Close an application (params: app_name, force)
- "create_file": Create a file (params: file_path, content)
- "read_file": Read a file (params: file_path)
- "modify_file": Replace file content (params: file_path, content)
- "append_file": Append to file (params: file_path, content)
- "delete_file": Delete a file (params: file_path)
- "open_file": Open a file or directory with the default app (params: file_path)
- "create_directory": Create directory (params: dir_path)
- "delete_directory": Delete directory (params: dir_path, recursive)
- "list_directory": List directory contents (params: dir_path)
- "search_files": Search for files (params: directory, pattern)
- "open_url": Open a URL (params: url)
- "chat": Just answer a question or have a conversation (no params needed)
- "clarify": Ask the user a brief question to clarify intent before acting (params: question)

For conversational messages where no action is needed, use the "chat" action and put the final answer in "explanation". Do not suggest or perform other actions when a direct answer suffices.
If additional context or a task plan is provided, use it to pick sensible defaults (paths, filenames, tools) and prefer safer options first.
Use paths relative to the current working directory unless the user provided an absolute path. Do NOT invent parent paths (\"../\") if the user did not request them; ask a clarifying question instead.

Examples:

User: "open my email"
{
    "action": "open_app",
    "parameters": {"app_name": "mail"},
    "explanation": "Opening your email client"
}

User: "create a hello world Python script"
{
    "action": "create_file",
    "parameters": {
        "file_path": "hello.py",
        "content": "print('Hello, World!')"
    },
    "explanation": "Creating hello.py with a simple print statement"
}

User: "what's the weather today?"
{
    "action": "chat",
    "parameters": {},
    "explanation": "I don't have access to real-time weather data, but I can help you open a weather website or application if you'd like!"
}

User: "what is 2+2?"
```json
{
    "action": "chat",
    "parameters": {},
    "explanation": "2 + 2 = 4."
}
```

Always wrap your JSON response in ```json``` code blocks, with nothing before or after the code block."""

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

        # Set system prompt
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
            # Get AI response
            ai_response = self.ollama.chat(
                self._build_augmented_prompt(user_input, context, plan)
            )

            action_data = self._parse_ai_response(ai_response)

            if not action_data:
                # If parsing failed, return the AI response as-is
                return ai_response

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
        parts = [
            f"{user_input}\n(Current working directory: {cwd}. Use relative paths here unless given an absolute path.)"
        ]

        # Ask clarifying questions when needed
        parts.append(
            "Before acting, briefly ask any needed clarifying questions (one message) "
            "if the request is ambiguous or paths are unclear. Otherwise act directly."
        )
        parts.append(
            "Use paths relative to the current working directory provided above; do not use '../' "
            "unless explicitly requested. If a file is not found, ask which path to use."
        )

        if plan:
            try:
                plan_preview = json.dumps(plan, ensure_ascii=True)
            except Exception:
                plan_preview = str(plan)
            parts.append(f"Current task plan: {plan_preview}")

        if context:
            recent = context[-6:]  # limit to keep prompt compact
            context_lines = []
            for item in recent:
                role = item.get("role", "user")
                content = item.get("content", "")
                context_lines.append(f"{role}: {content}")
            parts.append("Recent context:\n" + "\n".join(context_lines))

        parts.append(
            "Act now: produce exactly one JSON action object per system prompt, "
            "wrapped in ```json``` with nothing else. Do not repeat or restate the task plan."
        )

        return "\n\n".join(parts)

    def _parse_ai_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response to extract action data.

        Args:
            response: Raw AI response.

        Returns:
            Parsed action data or None if parsing failed.
        """
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
                    return block

            # Fall back to the first parsed block (e.g., plan JSON without action)
            if parsed_blocks:
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
                    return normalized
                return {
                    "action": "chat",
                    "parameters": {},
                    "explanation": response.strip()
                }

            # Not structured JSON, treat as chat response
            return {
                "action": "chat",
                "parameters": {},
                "explanation": response.strip()
            }

        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return None

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

        # Handle chat action
        if action == "chat":
            return explanation

        # Create operation for safety check
        operation = self._create_operation(action, params)

        if not operation:
            if action == "clarify":
                question = explanation or params.get("question") or "Could you clarify?"
                return question
            return f"Unknown action: {action}"

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
        except Exception as e:
            self.safety.log_operation(operation, False, str(e))
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
            "open_app": (OperationType.APP_OPEN, "app_name"),
            "close_app": (OperationType.APP_CLOSE, "app_name"),
            "create_file": (OperationType.FILE_CREATE, "file_path"),
            "append_file": (OperationType.FILE_APPEND, "file_path"),
            "read_file": (OperationType.FILE_READ, "file_path"),
            "modify_file": (OperationType.FILE_MODIFY, "file_path"),
            "delete_file": (OperationType.FILE_DELETE, "file_path"),
            "open_file": (OperationType.FILE_OPEN, "file_path"),
            "create_directory": (OperationType.DIR_CREATE, "dir_path"),
            "delete_directory": (OperationType.DIR_DELETE, "dir_path"),
            "list_directory": (OperationType.DIR_LIST, "dir_path"),
            "search_files": (OperationType.FILE_SEARCH, "directory"),
            "open_url": (OperationType.BROWSER_OPEN, "url"),
            "clarify": (OperationType.FILE_READ, "question"),  # benign placeholder
        }

        if action not in action_map:
            return None

        op_type, target_key = action_map[action]
        target = params.get(target_key, "unknown")

        return Operation(op_type, target, params)

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
                success, message = self.app_controller.open_url(params["url"])

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
