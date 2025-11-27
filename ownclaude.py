#!/usr/bin/env python3
"""PBOS AI (Personal Bot Operating System) - fast CLI assistant with memory and planning."""

import sys
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import argparse
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from loguru import logger

from ownclaude.core.config import ConfigManager, Config
from ownclaude.core.ollama_client import OllamaClient
from ownclaude.core.safety import SafetyManager
from ownclaude.core.executor import CommandExecutor


class OwnClaude:
    """Main PBOS AI application with enhanced memory and planning capabilities."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize PBOS AI.

        Args:
            config_path: Path to configuration file.
        """
        self.console = Console()
        self.config_manager = ConfigManager(config_path)
        self.config: Optional[Config] = None
        self.ollama: Optional[OllamaClient] = None
        self.safety: Optional[SafetyManager] = None
        self.executor: Optional[CommandExecutor] = None

        # Enhanced features
        self.current_plan: Optional[Dict[str, Any]] = None
        self.session_context: Dict[str, Any] = {}
        self.show_task_plan: bool = True
        self.exit_requested: bool = False
        self.max_runtime_seconds: int = 300  # Increased from 90 to 300 seconds (5 minutes)
        self.recommended_models = {
            "fast": ["phi3:mini", "gemma2:2b", "llama3.2:3b"],
            "balanced": ["llama3.1:8b", "mistral:7b", "qwen2.5:7b"],
            "claude_like": ["gpt-oss:120b-cloud", "llama3.1:70b", "deepseek-coder:33b"],
        }

    def initialize(self) -> bool:
        """Initialize the application.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        try:
            # Load configuration
            self.config = self.config_manager.load()

            # Setup logging
            self._setup_logging()

            # Initialize components
            self.ollama = OllamaClient(self.config)
            self.safety = SafetyManager(self.config)
            self.executor = CommandExecutor(self.config, self.ollama, self.safety)

            # Check Ollama connection
            self.console.print("[yellow]Checking connection to Ollama...[/yellow]")
            if not self.ollama.check_connection():
                self.console.print("[red]Failed to connect to Ollama![/red]")
                self.console.print(
                    "[yellow]Please ensure Ollama is running. "
                    "Run 'ollama serve' if using local model.[/yellow]"
                )
                return False

            self.console.print("[green]✓ Connected to Ollama[/green]")

            # Warn about small models
            self._check_model_quality()

            return True

        except FileNotFoundError as e:
            self.console.print(f"[red]Error: {e}[/red]")
            self.console.print(
                "[yellow]Run 'python ownclaude.py --init-config' to create a default configuration.[/yellow]"
            )
            return False
        except Exception as e:
            self.console.print(f"[red]Initialization failed: {e}[/red]")
            logger.exception("Initialization error")
            return False

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_config = self.config.logging

        # Remove default handler
        logger.remove()

        # Add file handler
        log_file = Path(log_config.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            level=log_config.level,
            rotation=f"{log_config.max_size_mb} MB",
            retention=log_config.backup_count,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

        # Add console handler for errors
        logger.add(
            sys.stderr,
            level="ERROR",
            format="<red>{level}</red>: {message}"
        )

    def _check_model_quality(self) -> None:
        """Check if the model is suitable and warn if not."""
        model_name = self.config.ollama.local.model if self.config.model_type == "local" else self.config.ollama.cloud.model

        # Models known to be too small
        small_models = ["3b", ":3b", "tiny", "mini"]
        is_small = any(marker in model_name.lower() for marker in small_models)

        # Recommended models
        good_models = ["llama3.1:8b", "mistral:7b", "qwen2.5:7b", "deepseek-coder", ":8b", ":7b", "13b", "70b"]
        is_good = any(marker in model_name.lower() for marker in good_models)

        if is_small:
            self.console.print()
            self.console.print("[bold red]⚠️  WARNING: Small Model Detected![/bold red]")
            self.console.print(f"[yellow]You're using: {model_name}[/yellow]")
            self.console.print("[yellow]Small models (<5B parameters) often:[/yellow]")
            self.console.print("[yellow]  • Open URLs instead of answering questions[/yellow]")
            self.console.print("[yellow]  • Provide empty or incomplete responses[/yellow]")
            self.console.print("[yellow]  • Don't follow instructions properly[/yellow]")
            self.console.print()
            self.console.print("[bold green]RECOMMENDED: Switch to llama3.1:8b or larger[/bold green]")
            self.console.print("[cyan]Quick fix:[/cyan]")
            self.console.print("[cyan]  1. Run: ollama pull llama3.1:8b[/cyan]")
            self.console.print("[cyan]  2. Edit config.json: \"model\": \"llama3.1:8b\"[/cyan]")
            self.console.print("[cyan]  3. Restart PBOS AI[/cyan]")
            self.console.print()
            self.console.print("[dim]See MODEL_GUIDE.md for more details[/dim]")
            self.console.print()

            # Pause to let user see the warning
            import time
            time.sleep(3)

        elif not is_good and self.config.model_type == "local":
            self.console.print()
            self.console.print(f"[yellow]ℹ️  Using model: {model_name}[/yellow]")
            self.console.print("[yellow]For best results, we recommend llama3.1:8b or mistral:7b[/yellow]")
            self.console.print("[dim]See MODEL_GUIDE.md for recommendations[/dim]")
            self.console.print()

    def _switch_model_source(self, target: str) -> None:
        """Switch between local and cloud inference on the fly."""
        target = target.lower()
        if target not in {"local", "cloud"}:
            self.console.print("[red]Model source must be 'local' or 'cloud'.[/red]")
            return

        if target == self.config.model_type:
            self.console.print(f"[green]Already using {target} models.[/green]")
            return

        try:
            self.ollama.switch_mode(target)
            self.executor.update_ollama_client(self.ollama)
            self.config.model_type = target
            connection_ok = self.ollama.check_connection()
            if connection_ok:
                self.console.print(f"[green]✓ Switched to {target} mode and connection verified.[/green]")
            else:
                self.console.print(f"[yellow]Switched to {target} mode, but connection could not be verified.[/yellow]")
        except Exception as exc:
            self.console.print(f"[red]Failed to switch model source: {exc}[/red]")
            logger.exception("Model switch failed")

    def _set_model_name(self, model_name: str) -> None:
        """Update the default model for the current mode."""
        if not model_name:
            self.console.print("[red]Please provide a model name.[/red]")
            return

        try:
            self.ollama.set_default_model(model_name)
            self.console.print(f"[green]✓ Using model: {model_name}[/green]")
            self._check_model_quality()
        except Exception as exc:
            self.console.print(f"[red]Failed to set model: {exc}[/red]")
            logger.exception("Model set failed")

    def _show_model_info(self) -> None:
        """Display active model settings and recommendations."""
        table = Table(title="Model Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        mode = self.config.model_type
        active_model = self.config.ollama.local.model if mode == "local" else self.config.ollama.cloud.model
        table.add_row("Mode", mode.capitalize())
        table.add_row("Active Model", active_model)
        if mode == "local":
            table.add_row("Endpoint", self.config.ollama.local.host)
        else:
            table.add_row("Endpoint", self.config.ollama.cloud.endpoint)
        table.add_row("Routing", "✓ Enabled" if getattr(self.config, "enable_model_routing", False) else "✗ Disabled")

        rec_lines = []
        for label, models in self.recommended_models.items():
            rec_lines.append(f"{label.title()}: {', '.join(models)}")

        self.console.print(table)
        self.console.print(Panel(
            "\n".join(rec_lines),
            title="[bold cyan]Suggested Models[/bold cyan]",
            border_style="cyan"
        ))

    def _get_active_model_config(self):
        """Return the active model configuration (local or cloud)."""
        return self.config.ollama.local if self.config.model_type == "local" else self.config.ollama.cloud

    def _run_with_timeout(self, user_input: str, allow_fallback: bool = True) -> str:
        """Execute the command with a hard timeout to avoid hangs."""
        active_model_config = self._get_active_model_config()
        timeout = getattr(active_model_config, "timeout", None) or self.max_runtime_seconds

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                self.executor.execute_command,
                user_input,
                self.ollama.get_display_history(),
                self.current_plan,
            )

            try:
                return future.result(timeout=timeout)
            except KeyboardInterrupt:
                future.cancel()
                self.exit_requested = True
                raise
            except FuturesTimeout:
                future.cancel()
                if allow_fallback and self.config.model_type == "local":
                    self.console.print(
                        "[yellow]Local response timed out. Trying cloud instead...[/yellow]"
                    )
                    try:
                        self._switch_model_source("cloud")
                        return self._run_with_timeout(user_input, allow_fallback=False)
                    except Exception as fallback_exc:
                        self.console.print(f"[red]Cloud fallback failed: {fallback_exc}[/red]")
                else:
                    self.console.print(
                        "[red]Response took too long and was cancelled. Try 'use cloud' for faster answers or switch to a smaller local model.[/red]"
                    )
                raise
            except TypeError:
                # Fallback for executors that don't accept extra parameters
                future = executor.submit(self.executor.execute_command, user_input)
                try:
                    return future.result(timeout=timeout)
                except FuturesTimeout:
                    future.cancel()
                    if allow_fallback and self.config.model_type == "local":
                        self.console.print(
                            "[yellow]Local response timed out. Trying cloud instead...[/yellow]"
                        )
                        try:
                            self._switch_model_source("cloud")
                            return self._run_with_timeout(user_input, allow_fallback=False)
                        except Exception as fallback_exc:
                            self.console.print(f"[red]Cloud fallback failed: {fallback_exc}[/red]")
                    else:
                        self.console.print(
                            "[red]Response took too long and was cancelled. Try 'use cloud' for faster answers or switch to a smaller local model.[/red]"
                        )
                    raise
            except Exception as exc:
                future.cancel()
                # If local failed, try automatic cloud fallback once
                if allow_fallback and self.config.model_type == "local":
                    self.console.print(
                        f"[yellow]Local model failed ({exc}). Trying cloud instead...[/yellow]"
                    )
                    try:
                        self._switch_model_source("cloud")
                        return self._run_with_timeout(user_input, allow_fallback=False)
                    except Exception as fallback_exc:
                        self.console.print(f"[red]Cloud fallback failed: {fallback_exc}[/red]")
                raise
    def _plan_task(self, user_input: str) -> Dict[str, Any]:
        """Generate a task plan before execution."""
        self.console.print("[cyan]Creating task plan...[/cyan]")

        planning_prompt = f"""
You are an AI assistant that creates detailed plans before executing tasks.
Given this request: "{user_input}"

Create a structured plan with:
1. Goal Analysis: What exactly needs to be accomplished?
2. Steps Required: Break down into specific actionable steps
3. Potential Risks: Any safety concerns or edge cases
4. Expected Outcome: What success looks like
5. Required Tools: What system tools or commands might be needed
6. Approach: Brief reasoning path you will follow (knowledge sources, checks, or shortcuts)

Format your response as JSON:
{{
    "goal_analysis": "...",
    "approach": "...",
    "steps": ["step1", "step2", "..."],
    "risks": ["risk1", "risk2", "..."],
    "expected_outcome": "...",
    "required_tools": ["tool1", "tool2", "..."]
}}
"""

        try:
            plan_response = self.ollama.chat(planning_prompt)
            return json.loads(plan_response)
        except Exception as e:
            logger.warning(f"Plan generation failed: {e}")
            return {
                "goal_analysis": "Direct execution",
                "approach": "Use prior knowledge to answer directly.",
                "steps": [user_input],
                "risks": [],
                "expected_outcome": "Task completion",
                "required_tools": []
            }

    def _diagnose_issue(self, problem_description: str) -> str:
        """Diagnose computer issues and suggest solutions."""
        self.console.print("[cyan]Analyzing system issue...[/cyan]")

        diagnostic_prompt = f"""
You are a system administrator and developer. Diagnose this issue:

"{problem_description}"

Provide:
1. Likely causes
2. Diagnostic commands to run
3. Step-by-step solutions
4. Prevention measures

Format your response clearly with headers and bullet points.
"""

        return self.ollama.chat(diagnostic_prompt)

    def _review_code(self, code: str, language: str = "python", task: str = "") -> str:
        """Perform code review with security and best practices."""
        self.console.print("[cyan]Reviewing code...[/cyan]")

        review_prompt = f"""
Review this {language} code for:
1. Security vulnerabilities
2. Best practices
3. Performance issues
4. Maintainability
5. Error handling
6. Code clarity and documentation

{"Task context: " + task if task else ""}

Code:
```{language}
{code}
```

Provide specific suggestions for improvement with examples.
"""
        return self.ollama.chat(review_prompt)

    def _analyze_code_issues(self, code: str, error: Optional[str] = None) -> str:
        """Analyze code and suggest fixes."""
        self.console.print("[cyan]Analyzing code issues...[/cyan]")

        prompt = f"""
Analyze this code and identify issues:

{code}
{"Error message: " + error if error else ""}

Provide:
- Issues found with line numbers
- Specific fixes with code examples
- Best practices improvements
- Security considerations
- Performance optimizations
"""
        return self.ollama.chat(prompt)

    def _execute_diagnostics(self, commands: List[str]) -> Dict[str, Any]:
        """Safely execute diagnostic commands and return results."""
        self.console.print("[cyan]Running diagnostics...[/cyan]")
        results: Dict[str, Any] = {}

        for cmd in commands:
            try:
                if self._is_safe_diagnostic(cmd):
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    results[cmd] = {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                else:
                    results[cmd] = {"error": "Command not allowed for security reasons"}
            except Exception as e:
                results[cmd] = {"error": str(e)}
        return results

    def _is_safe_diagnostic(self, command: str) -> bool:
        """Check if a diagnostic command is safe to execute."""
        safe_commands = [
            "dir", "ls", "ps", "top", "df", "du", "netstat", "ping",
            "tasklist", "systeminfo", "wmic", "get-process", "get-service"
        ]

        command_lower = command.lower().strip()
        return any(cmd in command_lower for cmd in safe_commands)

    def _is_chat_question(self, user_input: str) -> bool:
        """Determine if input is a chat question vs an action request.

        Args:
            user_input: The user's input.

        Returns:
            True if this appears to be a question.
        """
        question_indicators = ["what", "why", "how", "when", "where", "who", "tell me", "explain", "can you", "could you", "would you", "help me"]
        action_indicators = [
            "create", "make", "write", "build", "delete", "modify", "open", "run",
            "update", "edit", "change", "fix", "improve", "add", "remove"
        ]
        creative_requests = [
            "story", "poem", "song", "lyrics", "essay", "script", "scene",
            "joke", "tweet", "post", "narrative", "chapter", "fanfic", "fan fiction"
        ]

        input_lower = user_input.lower().strip()

        # Treat obvious question phrasing as a chat request, even if it contains action verbs
        starts_like_question = input_lower.startswith(tuple(question_indicators))
        has_question_mark = input_lower.endswith("?")
        has_question_phrase = any(
            phrase in input_lower for phrase in ["how do i", "how to", "what is", "tell me", "help me"]
        )

        has_action = any(word in input_lower for word in action_indicators)
        is_creative = any(word in input_lower for word in creative_requests)

        # Creative writing requests should be treated as chat (streamed) even if they contain action verbs
        if is_creative:
            return True

        # Creative writing should be treated as chat even if it contains "write/make"
        if has_action:
            return False

        # Otherwise fall back to question detection.
        return starts_like_question or has_question_mark or has_question_phrase

    def _prompt_destination(self, session: "PromptSession") -> Optional[str]:
        """Ask the user where to route the current chat question."""
        if not getattr(self.config.interface, "ask_destination", True):
            return None

        default = self.config.model_type
        prompt = (
            f"Route this question to [local/cloud]? Press Enter to keep {default}: "
        )

        try:
            choice = session.prompt(prompt)
        except (KeyboardInterrupt, EOFError):
            self.console.print("[yellow]Keeping current model source.[/yellow]")
            return None

        choice = choice.strip().lower()
        if not choice:
            return None

        if choice in {"local", "cloud"}:
            return choice

        self.console.print("[yellow]Unrecognized option. Keeping current model source.[/yellow]")
        return None

    def _execute_with_streaming(self, user_input: str, start_time: float) -> str:
        """Execute command and stream the response in real-time.

        Args:
            user_input: The user's input.
            start_time: When execution started.

        Returns:
            The complete response.
        """
        from rich.live import Live
        from rich.text import Text

        # Build the prompt
        prompt = self.executor._build_augmented_prompt(
            user_input,
            self.ollama.get_display_history(),
            self.current_plan
        )

        # Stream the response
        full_response = ""
        display_text = Text()

        try:
            with Live(display_text, console=self.console, refresh_per_second=10) as live:
                for chunk in self.ollama.chat(prompt, stream=True):
                    full_response += chunk
                    display_text.append(chunk)
                    live.update(display_text)
        except KeyboardInterrupt:
            self.exit_requested = True
            raise
        except TimeoutError:
            self.console.print(
                "\n[red]The model stopped responding. Trying a non-streamed retry...[/red]"
            )
            fallback_response = self._run_with_timeout(user_input)
            elapsed_time = time.time() - start_time
            time_str = f"{elapsed_time*1000:.0f}ms" if elapsed_time < 1 else f"{elapsed_time:.2f}s"
            self._print_response_panel(fallback_response, time_str)
            return fallback_response
        except Exception as exc:
            self.console.print(
                f"\n[red]Streaming failed ({exc}). Trying a non-streamed retry...[/red]"
            )
            fallback_response = self._run_with_timeout(user_input)
            elapsed_time = time.time() - start_time
            time_str = f"{elapsed_time*1000:.0f}ms" if elapsed_time < 1 else f"{elapsed_time:.2f}s"
            self._print_response_panel(fallback_response, time_str)
            return fallback_response

        # Parse to extract explanation if it's JSON
        action_data = self.executor._parse_ai_response(full_response)
        if action_data and action_data.get("action") == "chat":
            final_response = action_data.get("explanation", full_response)
        else:
            final_response = full_response

        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        if elapsed_time < 1:
            time_str = f"{elapsed_time*1000:.0f}ms"
        else:
            time_str = f"{elapsed_time:.2f}s"

        # Show final formatted response
        self._print_response_panel(final_response, time_str)

        return final_response

    def _print_response_panel(self, content: str, time_str: str) -> None:
        """Render bot responses in purple with Markdown formatting."""
        try:
            renderable = Markdown(content, code_theme="monokai")
        except Exception:
            renderable = content

        self.console.print()
        self.console.print(Panel(
            renderable,
            title=f"[bold magenta]PBOS AI[/bold magenta] [dim]({time_str})[/dim]",
            border_style="magenta",
            style="magenta"
        ))
        self.console.print()

    def run(self) -> None:
        """Run the interactive CLI with enhanced capabilities."""
        self._print_banner()

        history_file = Path.home() / ".pbos_history"
        kb = KeyBindings()

        @kb.add('f2')
        def _(event) -> None:
            """Toggle task plan display with F2 (avoid backspace conflict)."""
            self.show_task_plan = not self.show_task_plan
            status = "shown" if self.show_task_plan else "hidden"
            self.console.print(f"[dim]Task plan preview {status} (F2).[/dim]")

        @kb.add('c-c')
        def _(event) -> None:
            """Exit application on Ctrl+C."""
            self.exit_requested = True
            self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
            event.app.exit()

        session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            key_bindings=kb,
        )

        self.console.print("\n[cyan]Type your commands or 'help' for assistance. "
                          "Type 'exit' or 'quit' to leave.[/cyan]\n")

        while True:
            try:
                user_input = session.prompt("You: ")

                # Handle Ctrl+C or None input
                if user_input is None or self.exit_requested:
                    self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
                    break

                user_input = user_input.strip()
                if not user_input:
                    continue

                lower_input = user_input.lower()

                # User input will be added to history in the chat call

                # Special commands
                if lower_input in ['exit', 'quit', 'q']:
                    self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
                    break
                if lower_input == 'help':
                    self._show_help()
                    continue
                if lower_input == 'clear':
                    self.console.clear()
                    self._print_banner()
                    continue
                if lower_input == 'history':
                    self._show_history()
                    continue
                if lower_input == 'status':
                    self._show_status()
                    continue
                if lower_input in ['model', 'models']:
                    self._show_model_info()
                    continue
                if lower_input in ['use cloud', 'cloud mode']:
                    self._switch_model_source('cloud')
                    continue
                if lower_input in ['use local', 'local mode']:
                    self._switch_model_source('local')
                    continue
                if lower_input.startswith('set model'):
                    _, _, model_name = user_input.partition('set model')
                    self._set_model_name(model_name.strip())
                    continue
                if lower_input == 'memory':
                    self._show_memory()
                    continue
                if lower_input == 'plan':
                    self._show_current_plan()
                    continue
                if lower_input == 'plan off':
                    self.show_task_plan = False
                    self.console.print("[dim]Task plan preview hidden.[/dim]")
                    continue
                if lower_input == 'plan on':
                    self.show_task_plan = True
                    self.console.print("[dim]Task plan preview shown.[/dim]")
                    continue
                if lower_input == 'plan toggle':
                    self.show_task_plan = not self.show_task_plan
                    status = "shown" if self.show_task_plan else "hidden"
                    self.console.print(f"[dim]Task plan preview {status}.[/dim]")
                    continue
                if lower_input.startswith('rollback'):
                    parts = user_input.split()
                    if len(parts) > 1:
                        self._rollback_operation(parts[1])
                    else:
                        self.console.print("[red]Usage: rollback <operation_id>[/red]")
                    continue
                if lower_input.startswith('diagnose'):
                    problem = user_input[9:].strip()
                    self._handle_diagnosis(problem)
                    continue
                if lower_input.startswith('review'):
                    self._handle_code_review(user_input)
                    continue

                # Start timing
                start_time = time.time()

                # Plan task if enabled (default False for speed)
                if getattr(self.config.features, "enable_task_planning", False):
                    with self.console.status("[cyan]Planning task...[/cyan]"):
                        self.current_plan = self._plan_task(user_input)

                    if self.config.interface.show_timestamps:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        self.console.print(f"[dim]{timestamp}[/dim]")

                    if self.show_task_plan:
                        self._print_plan_preview(self.current_plan)

                # Execute command with streaming for better UX
                # Detect if this is likely a chat question vs an action
                is_chat_question = self._is_chat_question(user_input)

                if is_chat_question:
                    route_choice = self._prompt_destination(session)
                    if route_choice and route_choice != self.config.model_type:
                        self._switch_model_source(route_choice)

                    # Prefer streaming for cloud, use non-stream for local to avoid stalls
                    if self.config.model_type == "cloud":
                        response = self._execute_with_streaming(user_input, start_time)
                    else:
                        with self.console.status("[cyan]Thinking...[/cyan]"):
                            response = self._run_with_timeout(user_input)

                        elapsed_time = time.time() - start_time
                        time_str = f"{elapsed_time*1000:.0f}ms" if elapsed_time < 1 else f"{elapsed_time:.2f}s"
                        self._print_response_panel(response, time_str)
                else:
                    # Use normal execution for actions
                    with self.console.status("[cyan]Thinking...[/cyan]"):
                        response = self._run_with_timeout(user_input)

                    # Calculate elapsed time
                    elapsed_time = time.time() - start_time

                    # Format elapsed time nicely
                    if elapsed_time < 1:
                        time_str = f"{elapsed_time*1000:.0f}ms"
                    else:
                        time_str = f"{elapsed_time:.2f}s"

                    self._print_response_panel(response, time_str)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Exiting...[/yellow]")
                break
            except EOFError:
                break
            except FuturesTimeout:
                # Already messaged the user in _run_with_timeout
                continue
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                logger.exception("Runtime error")

    def _print_banner(self) -> None:
        """Print application banner."""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                     PBOS AI — Personal Bot OS                ║
║    Precision • Bandwidth • Orchestration • Speed • Stream    ║
║        Terminal-native copilot with instant routing          ║
╚══════════════════════════════════════════════════════════════╝
        """
        art = r"""
__/\\\\\\\\\\\\\____/\\\\\\\\\\\\\_________/\\\\\__________/\\\\\\\\\\\___        
 _\/\\\/////////\\\_\/\\\/////////\\\_____/\\\///\\\______/\\\/////////\\\_       
  _\/\\\_______\/\\\_\/\\\_______\/\\\___/\\\/__\///\\\___\//\\\______\///__      
   _\/\\\\\\\\\\\\\/__\/\\\\\\\\\\\\\\___/\\\______\//\\\___\////\\\_________     
    _\/\\\/////////____\/\\\/////////\\\_\/\\\_______\/\\\______\////\\\______    
     _\/\\\_____________\/\\\_______\/\\\_\//\\\______/\\\__________\////\\\___   
      _\/\\\_____________\/\\\_______\/\\\__\///\\\__/\\\_____/\\\______\//\\\__  
       _\/\\\_____________\/\\\\\\\\\\\\\/_____\///\\\\\/_____\///\\\\\\\\\\\/___ 
        _\///______________\/////////////_________\/////_________\///////////_____ 
        """
        self.console.print(f"[bold cyan]{banner}[/bold cyan]")
        self.console.print(f"[cyan]{art}[/cyan]")

        model_type = self.config.model_type
        model_name = (self.config.ollama.local.model if model_type == "local"
                     else self.config.ollama.cloud.model)
        self.console.print(f"[dim]Using {model_type} model: {model_name}[/dim]")
        self.console.print(f"[dim]Context messages: {self.ollama.get_history_count()}[/dim]")

    def _format_plan_steps(
        self,
        steps: List[Any],
        max_steps: Optional[int] = None
    ) -> tuple[list[str], bool]:
        """Format plan steps into readable lines."""
        formatted: list[str] = []
        for idx, step in enumerate(steps):
            if max_steps is not None and idx >= max_steps:
                break
            title = f"Step {idx + 1}"
            desc = ""
            if isinstance(step, dict):
                title = step.get("step") or step.get("title") or step.get("name") or title
                desc = step.get("description") or step.get("details") or ""
            else:
                title = str(step)
                desc = ""

            line = f"{idx + 1}. {title}"
            if desc and desc != title:
                line += f" — {desc}"
            formatted.append(line)

        truncated = max_steps is not None and len(steps) > max_steps
        return formatted, truncated

    def _print_plan_preview(self, plan: Dict[str, Any], show_all_steps: bool = False) -> None:
        """Render a task plan with approach and step insight."""
        if not plan:
            return

        goal = plan.get("goal_analysis", "N/A")
        approach = plan.get("approach") or plan.get("analysis") or ""
        expected = plan.get("expected_outcome", "N/A")
        steps = plan.get("steps", [])
        risks = plan.get("risks", [])
        tools = plan.get("required_tools", [])

        formatted_steps, truncated = self._format_plan_steps(
            steps,
            None if show_all_steps else 4
        )

        body_parts = [
            f"Goal: {goal}",
            f"Expected Outcome: {expected}",
        ]
        if approach:
            body_parts.append(f"Approach: {approach}")
        if formatted_steps:
            body_parts.append("Steps:\n" + "\n".join(formatted_steps))
        if truncated:
            body_parts.append(f"...and {len(steps) - len(formatted_steps)} more step(s).")
        if risks:
            risk_lines = "\n".join(f"• {r}" for r in risks)
            body_parts.append(f"Risks:\n{risk_lines}")
        if tools:
            body_parts.append("Tools: " + ", ".join(tools[:5]))

        self.console.print(Panel(
            "\n".join(body_parts),
            title="[bold blue]Task Plan[/bold blue]",
            border_style="blue"
        ))

    def _show_help(self) -> None:
        """Display enhanced help information."""
        help_text = """
PBOS AI Quick Guide

Natural Language Commands
You can control your computer using natural language:
- "open my email"
- "create a Python script that prints hello world"
- "close all browser windows"
- "list files in the current directory"
- "search for all Python files"

Special Commands
- help: Show this help message
- clear: Clear the screen
- status: Show system status and permissions
- model/models: Show current model settings and recommendations
- use cloud / use local: Toggle between cloud and local inference
- set model <name>: Override the default model for the active mode
- history: Show operation history
- memory: Show conversation memory/context
- plan: Show current task plan
- F2: Toggle task plan preview on/off
- Ctrl+C: Exit immediately
- plan off / plan on / plan toggle: Manage task plan preview
- diagnose <issue>: Diagnose system issues
- review <code/file>: Review code for issues
- rollback <id>: Rollback an operation
- exit/quit: Exit PBOS AI

Examples
- Open applications: "open calculator", "launch Excel"
- Open documents/folders: "open report.docx", "open the downloads folder"
- File operations: "create a file called notes.txt", "append 'done' to todo.md", "delete temp.txt"
- Information: "what files are in my downloads folder?"
- Coding: "write a Python function to calculate fibonacci"
- Diagnostics: "diagnose why my computer is slow"
- Code review: "review the script I just created"
"""
        self.console.print(Panel(
            Markdown(help_text),
            title="[bold cyan]Enhanced Help[/bold cyan]",
            border_style="cyan"
        ))

    def _show_status(self) -> None:
        """Display enhanced system status."""
        table = Table(title="System Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        perms = self.config.system_permissions
        mode = self.config.model_type
        active_model = self.config.ollama.local.model if mode == "local" else self.config.ollama.cloud.model
        table.add_row("Model Mode", mode.capitalize())
        table.add_row("Active Model", active_model)
        table.add_row("App Control", "✓ Enabled" if perms.allow_app_control else "✗ Disabled")
        table.add_row("File Operations", "✓ Enabled" if perms.allow_file_operations else "✗ Disabled")
        table.add_row("Browser Control", "✓ Enabled" if perms.allow_browser_control else "✗ Disabled")
        table.add_row("System Commands", "✓ Enabled" if perms.allow_system_commands else "✗ Disabled")

        features = self.config.features
        table.add_row("Rollback", "✓ Enabled" if self.config.security.enable_rollback else "✗ Disabled")
        table.add_row("Operation Logging", "✓ Enabled" if self.config.logging.log_operations else "✗ Disabled")
        table.add_row("Task Planning", "✓ Enabled" if getattr(features, "enable_task_planning", True) else "✗ Disabled")
        table.add_row("Context Memory", f"✓ {self.ollama.get_history_count()} messages")

        self.console.print(table)

    def _show_memory(self) -> None:
        """Show conversation memory."""
        conversation_history = self.ollama.get_display_history()
        if not conversation_history:
            self.console.print("[yellow]No conversation history.[/yellow]")
            return

        table = Table(title="Conversation Memory")
        table.add_column("Role", style="cyan")
        table.add_column("Content", style="green")
        table.add_column("Time", style="dim")

        for msg in conversation_history[-15:]:
            timestamp = msg.get('timestamp', '').split('T')[1].split('.')[0] if 'timestamp' in msg else 'N/A'
            content_preview = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
            table.add_row(msg['role'], content_preview, timestamp)

        self.console.print(table)

    def _show_current_plan(self) -> None:
        """Show current task plan."""
        if not self.current_plan:
            self.console.print("[yellow]No active task plan.[/yellow]")
            return

        self._print_plan_preview(self.current_plan, show_all_steps=True)

    def _show_history(self) -> None:
        """Display operation history."""
        history = self.safety.get_operation_history()

        if not history:
            self.console.print("[yellow]No operations in history.[/yellow]")
            return

        table = Table(title="Operation History")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Target", style="yellow")
        table.add_column("Time", style="dim")

        for op in history[-10:]:
            timestamp = op['timestamp'].split('T')[1].split('.')[0]
            table.add_row(
                op['id'][:8] + "...",
                op['type'],
                op['target'][:30],
                timestamp
            )

        self.console.print(table)

    def _rollback_operation(self, operation_id: str) -> None:
        """Rollback an operation.

        Args:
            operation_id: ID of operation to rollback.
        """
        with self.console.status("[cyan]Rolling back operation...[/cyan]"):
            success = self.safety.rollback_operation(operation_id)

        if success:
            self.console.print("[green]✓ Operation rolled back successfully[/green]")
        else:
            self.console.print("[red]✗ Failed to rollback operation[/red]")

    def _handle_diagnosis(self, problem: str) -> None:
        """Handle system diagnosis requests."""
        if not problem:
            self.console.print("[red]Please specify the problem to diagnose.[/red]")
            return

        start_time = time.time()
        with self.console.status("[cyan]Diagnosing issue...[/cyan]"):
            diagnosis = self._diagnose_issue(problem)
        elapsed_time = time.time() - start_time

        time_str = f"{elapsed_time*1000:.0f}ms" if elapsed_time < 1 else f"{elapsed_time:.2f}s"

        self.console.print(Panel(
            diagnosis,
            title=f"[bold red]System Diagnosis[/bold red] [dim]({time_str})[/dim]",
            border_style="red"
        ))

    def _handle_code_review(self, user_input: str) -> None:
        """Handle code review requests."""
        task_context = user_input[len("review"):].strip()

        start_time = time.time()
        with self.console.status("[cyan]Reviewing code...[/cyan]"):
            last_code = ""
            conversation_history = self.ollama.get_display_history()
            for msg in reversed(conversation_history):
                if msg['role'] == 'assistant' and '```' in msg['content']:
                    last_code = msg['content']
                    break

            if last_code:
                review = self._review_code(last_code, task=task_context)
                elapsed_time = time.time() - start_time
                time_str = f"{elapsed_time*1000:.0f}ms" if elapsed_time < 1 else f"{elapsed_time:.2f}s"

                self.console.print(Panel(
                    review,
                    title=f"[bold green]Code Review[/bold green] [dim]({time_str})[/dim]",
                    border_style="green"
                ))
            else:
                self.console.print("[yellow]No recent code found to review. Please provide code directly.[/yellow]")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PBOS AI - Your personal terminal copilot"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to configuration file (default: config.json)"
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Create a default configuration file"
    )

    args = parser.parse_args()

    # Handle config initialization
    if args.init_config:
        config_path = args.config or Path("config.json")
        if config_path.exists():
            print(f"Configuration file already exists: {config_path}")
            response = input("Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return

        ConfigManager.create_default_config(config_path)
        print(f"Created configuration file: {config_path}")
        print("Please edit the configuration file with your settings.")
        return

    app = OwnClaude(args.config)

    if not app.initialize():
        sys.exit(1)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
