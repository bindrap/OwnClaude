#!/usr/bin/env python3
"""OwnClaude - Your personal AI assistant for computer control."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import argparse
from datetime import datetime
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
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
    """Main OwnClaude application."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize OwnClaude.

        Args:
            config_path: Path to configuration file.
        """
        self.console = Console()
        self.config_manager = ConfigManager(config_path)
        self.config: Optional[Config] = None
        self.ollama: Optional[OllamaClient] = None
        self.safety: Optional[SafetyManager] = None
        self.executor: Optional[CommandExecutor] = None

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

    def run(self) -> None:
        """Run the interactive CLI."""
        self._print_banner()

        # Setup prompt session
        history_file = Path.home() / ".ownclaude_history"
        session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
        )

        self.console.print("\n[cyan]Type your commands or 'help' for assistance. "
                          "Type 'exit' or 'quit' to leave.[/cyan]\n")

        while True:
            try:
                # Get user input
                user_input = session.prompt("You: ").strip()

                if not user_input:
                    continue

                # Check for special commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
                    break

                elif user_input.lower() == 'help':
                    self._show_help()
                    continue

                elif user_input.lower() == 'clear':
                    self.console.clear()
                    self._print_banner()
                    continue

                elif user_input.lower() == 'history':
                    self._show_history()
                    continue

                elif user_input.lower() == 'status':
                    self._show_status()
                    continue

                elif user_input.lower().startswith('rollback'):
                    parts = user_input.split()
                    if len(parts) > 1:
                        self._rollback_operation(parts[1])
                    else:
                        self.console.print("[red]Usage: rollback <operation_id>[/red]")
                    continue

                # Execute command
                if self.config.interface.show_timestamps:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    self.console.print(f"[dim]{timestamp}[/dim]")

                with self.console.status("[cyan]Thinking...[/cyan]"):
                    response = self.executor.execute_command(user_input)

                # Display response
                self.console.print(Panel(
                    response,
                    title="[bold cyan]OwnClaude[/bold cyan]",
                    border_style="cyan"
                ))
                self.console.print()

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' or 'quit' to leave.[/yellow]")
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                logger.exception("Runtime error")

    def _print_banner(self) -> None:
        """Print application banner."""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                        OwnClaude                          ║
║                                                           ║
║     Your Personal AI Assistant for Computer Control      ║
╚═══════════════════════════════════════════════════════════╝
        """
        self.console.print(f"[bold cyan]{banner}[/bold cyan]")

        # Show model info
        model_type = self.config.model_type
        model_name = (self.config.ollama.local.model if model_type == "local"
                     else self.config.ollama.cloud.model)
        self.console.print(f"[dim]Using {model_type} model: {model_name}[/dim]")

    def _show_help(self) -> None:
        """Display help information."""
        help_text = """
# OwnClaude Help

## Natural Language Commands
You can control your computer using natural language:
- "open my email"
- "create a Python script that prints hello world"
- "close all browser windows"
- "list files in the current directory"
- "search for all Python files"

## Special Commands
- **help**: Show this help message
- **clear**: Clear the screen
- **status**: Show system status and permissions
- **history**: Show operation history
- **rollback <id>**: Rollback an operation
- **exit/quit**: Exit OwnClaude

## Examples
- Open applications: "open calculator", "launch Excel"
- File operations: "create a file called notes.txt", "delete temp.txt"
- Information: "what files are in my downloads folder?"
- Coding: "write a Python function to calculate fibonacci"
        """
        self.console.print(Panel(
            Markdown(help_text),
            title="[bold cyan]Help[/bold cyan]",
            border_style="cyan"
        ))

    def _show_status(self) -> None:
        """Display system status."""
        table = Table(title="System Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        # Permissions
        perms = self.config.system_permissions
        table.add_row("App Control", "✓ Enabled" if perms.allow_app_control else "✗ Disabled")
        table.add_row("File Operations", "✓ Enabled" if perms.allow_file_operations else "✗ Disabled")
        table.add_row("Browser Control", "✓ Enabled" if perms.allow_browser_control else "✗ Disabled")
        table.add_row("System Commands", "✓ Enabled" if perms.allow_system_commands else "✗ Disabled")

        # Features
        table.add_row("Rollback", "✓ Enabled" if self.config.security.enable_rollback else "✗ Disabled")
        table.add_row("Operation Logging", "✓ Enabled" if self.config.logging.log_operations else "✗ Disabled")

        self.console.print(table)

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

        for op in history[-10:]:  # Show last 10
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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OwnClaude - Your personal AI assistant"
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

    # Run application
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
