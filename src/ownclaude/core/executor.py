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
    SYSTEM_PROMPT = """You are OwnClaude, a powerful AI assistant that helps users control their computer and work with code through natural language commands.

Your role is to understand user requests and respond with exactly one structured action. You can:
1. Answer questions and provide information directly (MOST IMPORTANT - always prefer this for factual questions)
2. Create, read, modify, append, and delete files (and directories)
3. Open and close applications
4. Execute terminal commands, run tests, and build projects
5. Search code (grep), find definitions, and navigate codebases
6. Git operations (status, commit, branch, diff)
7. Analyze project structure and provide context
8. Ask clarifying questions when needed

CRITICAL RULES (YOU MUST FOLLOW THESE):
1. **CREATE CODE FILES DIRECTLY**: When user says "make/create/write a program/game/script", use "create_file" action and write the complete code. DO NOT use "open_app" to open IDEs (Eclipse, VS Code, etc.). DO NOT ask user to write code. You write the code directly.
2. **ANSWER QUESTIONS DIRECTLY**: For ANY factual question, use "chat" action with complete answer. DO NOT use "open_url", DO NOT search online, DO NOT open Wikipedia.
3. **NO EMPTY RESPONSES**: explanation field MUST contain actual content (50+ chars). NO placeholder text like "Providing an answer".
4. **FILE PATHS**: Use simple filenames in current directory like "test.txt". NEVER use "../" or parent paths.
5. **URLS ONLY WHEN ASKED**: Only use "open_url" when user EXPLICITLY says "open website" or "go to URL".

When a user asks you to perform an action, respond with a single JSON object in this format. Do not include multiple JSON objects or any text outside the code block.

{
    "action": "action_type",
    "parameters": {
        "param1": "value1",
        "param2": "value2"
    },
    "explanation": "Explanation of what you're doing (detailed for chat/questions, concise for actions)"
}

Available actions:
- "chat": Answer questions with DETAILED, COMPREHENSIVE responses (USE THIS FOR ALL FACTUAL QUESTIONS - provide thorough explanations, steps, examples)
- "create_file": Create a file in current directory (params: file_path, content) - file_path must be simple like "test.txt"
- "read_file": Read a file (params: file_path)
- "modify_file": Replace file content (params: file_path, content)
- "append_file": Append to file (params: file_path, content)
- "delete_file": Delete a file (params: file_path)
- "open_app": Open an application (params: app_name)
- "close_app": Close an application (params: app_name, force)
- "run_command": Execute a terminal command (params: command)
- "run_tests": Run project tests (params: test_command optional)
- "run_build": Build the project (params: build_command optional)
- "search_code": Search for code patterns (params: pattern, file_pattern optional)
- "find_definition": Find function/class definition (params: name, type optional)
- "get_project_summary": Get project structure summary (no params)
- "git_status": Get git repository status (no params)
- "git_diff": Get git diff (params: staged optional)
- "git_commit": Create a git commit (params: message)
- "analyze_file": Analyze a code file (params: file_path)
- "open_file": Open a file or directory with the default app (params: file_path)
- "create_directory": Create directory (params: dir_path)
- "delete_directory": Delete directory (params: dir_path, recursive)
- "list_directory": List directory contents (params: dir_path)
- "search_files": Search for files (params: directory, pattern)
- "open_url": Open a URL ONLY when explicitly requested (params: url)
- "clarify": Ask the user a brief question to clarify intent before acting (params: question)

Examples:

User: "how fast did Usain Bolt run?"
{
    "action": "chat",
    "parameters": {},
    "explanation": "Usain Bolt's fastest 100m time is 9.58 seconds, set at the 2009 World Championships in Berlin. His fastest 200m time is 19.19 seconds, also set in 2009."
}

User: "what is 2+2?"
{
    "action": "chat",
    "parameters": {},
    "explanation": "2 + 2 = 4."
}

User: "how do I change oil in my car?"
{
    "action": "chat",
    "parameters": {},
    "explanation": "To change your car's oil, follow these detailed steps:\n\n1. **Gather supplies**: Oil drain pan, socket wrench, new oil filter, correct type and amount of motor oil, funnel, and rags.\n\n2. **Prepare the car**: Warm up the engine by driving for 5 minutes, then park on a level surface and turn off the engine. Wait 5 minutes for oil to settle.\n\n3. **Locate the drain plug**: Look under the car near the front of the engine. The drain plug is typically a large bolt at the bottom of the oil pan.\n\n4. **Drain old oil**: Place the drain pan underneath, use a socket wrench to loosen the drain plug (turn counterclockwise), and let the oil fully drain for 10-15 minutes.\n\n5. **Replace drain plug**: Once drained, wipe the plug clean, replace the washer if needed, and tighten it securely (don't overtighten).\n\n6. **Change the filter**: Locate the oil filter (cylindrical canister), unscrew it by hand or with a filter wrench. Apply a thin layer of new oil to the rubber gasket of the new filter, then screw it in by hand until snug.\n\n7. **Add new oil**: Remove the oil filler cap on top of the engine. Use a funnel to pour in the correct amount of new oil (check your owner's manual for capacity).\n\n8. **Check oil level**: Replace the filler cap, start the engine for 30 seconds, turn it off, wait 2 minutes, then check the dipstick. Add more oil if needed to reach the \"Full\" mark.\n\n9. **Check for leaks**: Look under the car for any leaks around the drain plug and filter. If you see leaks, tighten as needed.\n\n10. **Dispose properly**: Take used oil to an auto parts store or recycling center for proper disposal.\n\nTypical interval: Every 5,000-7,500 miles or every 6 months."
}

User: "who was the first president?"
{
    "action": "chat",
    "parameters": {},
    "explanation": "George Washington was the first President of the United States, serving from 1789 to 1797."
}

User: "what's a good program to build 3D models and easy way to learn?"
{
    "action": "chat",
    "parameters": {},
    "explanation": "For 3D modeling, I recommend **Blender** (free, open-source, very powerful) as the best option for beginners. It has excellent free tutorials on YouTube (Blender Guru's 'Donut Tutorial' series) and official documentation. Other good options: **Tinkercad** (web-based, extremely simple for beginners), **SketchUp** (good for architectural modeling), and **Maya/3ds Max** (industry standard but expensive). Start with Blender - it's free and has the largest learning community."
}

User: "create a file called test.txt with hello world"
{
    "action": "create_file",
    "parameters": {
        "file_path": "test.txt",
        "content": "hello world"
    },
    "explanation": "Creating test.txt in the current directory"
}

User: "create a hello world Python script"
{
    "action": "create_file",
    "parameters": {
        "file_path": "hello.py",
        "content": "print('Hello, World!')"
    },
    "explanation": "Creating hello.py"
}

User: "make a Java game called flappy bird"
{
    "action": "create_file",
    "parameters": {
        "file_path": "FlappyBird.java",
        "content": "import javax.swing.*;\nimport java.awt.*;\nimport java.awt.event.*;\n\npublic class FlappyBird extends JPanel implements ActionListener, KeyListener {\n    private int birdY = 250;\n    private int velocity = 0;\n    private Timer timer;\n    \n    public FlappyBird() {\n        timer = new Timer(20, this);\n        timer.start();\n        addKeyListener(this);\n        setFocusable(true);\n    }\n    \n    public void actionPerformed(ActionEvent e) {\n        velocity += 1;\n        birdY += velocity;\n        repaint();\n    }\n    \n    public void keyPressed(KeyEvent e) {\n        if (e.getKeyCode() == KeyEvent.VK_SPACE) {\n            velocity = -10;\n        }\n    }\n    \n    public void keyReleased(KeyEvent e) {}\n    public void keyTyped(KeyEvent e) {}\n    \n    protected void paintComponent(Graphics g) {\n        super.paintComponent(g);\n        g.setColor(Color.RED);\n        g.fillOval(100, birdY, 30, 30);\n    }\n    \n    public static void main(String[] args) {\n        JFrame frame = new JFrame(\"Flappy Bird\");\n        FlappyBird game = new FlappyBird();\n        frame.add(game);\n        frame.setSize(800, 600);\n        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);\n        frame.setVisible(true);\n    }\n}"
    },
    "explanation": "Creating FlappyBird.java with game code"
}

User: "open my email"
{
    "action": "open_app",
    "parameters": {"app_name": "mail"},
    "explanation": "Opening your email client"
}

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

        # Initialize new enhanced modules
        self.project_context = ProjectContext()
        self.terminal_executor = TerminalExecutor()
        self.code_search = CodeSearch()
        self.git = GitIntegration()

        # Track last user input for validation
        self.last_user_input = ""

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
            f"{user_input}"
        ]

        # Emphasize current directory and path rules
        parts.append(
            f"\nIMPORTANT: You are working in directory: {cwd}"
        )
        parts.append(
            "For file operations, use ONLY simple filenames like 'test.txt' or 'script.py'. "
            "NEVER use '../' or parent directory paths. Files will be created in the current directory."
        )
        parts.append(
            "For factual questions, ALWAYS use the 'chat' action to answer directly. "
            "Do NOT open URLs or search online for factual questions."
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
            # Check if explanation is empty or just a placeholder
            if not explanation or len(explanation.strip()) < 10:
                return False, "The AI response was empty. Please try rephrasing your question or use a better model."

            # Check for common placeholder phrases that indicate no real answer
            placeholder_phrases = [
                "providing an answer",
                "let me answer",
                "i'll explain",
                "here's the answer",
                "opening",
                "searching for"
            ]

            explanation_lower = explanation.lower()
            # If it's very short and contains only placeholder text, it's invalid
            if len(explanation) < 50 and any(phrase in explanation_lower for phrase in placeholder_phrases):
                return False, "The AI didn't provide a complete answer. Please try: 1) Rephrasing your question, 2) Using a larger model (llama3.1:8b recommended), or 3) Being more specific."

        return True, explanation

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
