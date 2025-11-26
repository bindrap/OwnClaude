"""Terminal command execution with streaming output support."""

import os
import subprocess
import threading
import queue
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime

from loguru import logger


class CommandResult:
    """Result of a command execution."""

    def __init__(
        self,
        command: str,
        returncode: int,
        stdout: str,
        stderr: str,
        duration: float
    ):
        """Initialize command result.

        Args:
            command: Command that was executed.
            returncode: Exit code.
            stdout: Standard output.
            stderr: Standard error.
            duration: Execution duration in seconds.
        """
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.success = returncode == 0

    def __str__(self) -> str:
        """String representation."""
        status = "Success" if self.success else f"Failed (exit code: {self.returncode})"
        return f"{status}\nCommand: {self.command}\nDuration: {self.duration:.2f}s"


class TerminalExecutor:
    """Executes terminal commands with safety checks and streaming support."""

    # Dangerous commands that should be blocked
    DANGEROUS_COMMANDS = [
        'rm -rf /',
        'mkfs',
        'dd if=',
        'format',
        ':(){ :|:& };:',  # Fork bomb
        'chmod -R 777 /',
        'chown -R',
    ]

    # Safe commands that can be executed without confirmation
    SAFE_COMMANDS = [
        'ls', 'dir', 'cd', 'pwd', 'cat', 'echo', 'which', 'where',
        'git status', 'git log', 'git diff', 'git branch',
        'npm list', 'pip list', 'pip show',
        'python --version', 'node --version',
        'grep', 'find', 'locate',
    ]

    def __init__(self, working_directory: Optional[Path] = None):
        """Initialize terminal executor.

        Args:
            working_directory: Working directory for commands. Defaults to current directory.
        """
        self.working_directory = working_directory or Path.cwd()
        self.command_history: List[CommandResult] = []
        self.max_history = 100

    def is_safe_command(self, command: str) -> tuple[bool, Optional[str]]:
        """Check if a command is safe to execute.

        Args:
            command: Command to check.

        Returns:
            Tuple of (is_safe, reason).
        """
        command_lower = command.lower().strip()

        # Check dangerous commands
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous.lower() in command_lower:
                return False, f"Dangerous command detected: {dangerous}"

        # Check for potentially dangerous patterns
        if 'rm -rf' in command_lower and '/' in command_lower:
            return False, "Recursive deletion with absolute paths is not allowed"

        if command_lower.startswith('sudo '):
            return False, "sudo commands require manual execution for security"

        # Check for command injection attempts
        if any(char in command for char in [';', '&&', '||', '|', '`', '$(']):
            # Allow these in specific safe contexts
            if not any(safe in command_lower for safe in ['git', 'echo', 'grep', 'find']):
                return False, "Command chaining detected - please execute commands individually"

        return True, None

    def execute(
        self,
        command: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[int] = 300,
        check_safety: bool = True
    ) -> CommandResult:
        """Execute a command.

        Args:
            command: Command to execute.
            stream_callback: Optional callback for streaming output.
            timeout: Command timeout in seconds.
            check_safety: Whether to check command safety.

        Returns:
            CommandResult object.
        """
        logger.info(f"Executing command: {command}")

        # Safety check
        if check_safety:
            is_safe, reason = self.is_safe_command(command)
            if not is_safe:
                logger.warning(f"Command blocked: {reason}")
                return CommandResult(
                    command=command,
                    returncode=-1,
                    stdout="",
                    stderr=f"Command blocked for safety: {reason}",
                    duration=0.0
                )

        start_time = datetime.now()

        try:
            if stream_callback:
                result = self._execute_streaming(command, stream_callback, timeout)
            else:
                result = self._execute_standard(command, timeout)

            duration = (datetime.now() - start_time).total_seconds()

            cmd_result = CommandResult(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration
            )

            # Add to history
            self._add_to_history(cmd_result)

            return cmd_result

        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Command timed out after {timeout}s: {command}")
            return CommandResult(
                command=command,
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                duration=duration
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Command execution failed: {e}")
            return CommandResult(
                command=command,
                returncode=-1,
                stdout="",
                stderr=str(e),
                duration=duration
            )

    def _execute_standard(
        self,
        command: str,
        timeout: Optional[int]
    ) -> subprocess.CompletedProcess:
        """Execute command without streaming.

        Args:
            command: Command to execute.
            timeout: Timeout in seconds.

        Returns:
            CompletedProcess object.
        """
        return subprocess.run(
            command,
            shell=True,
            cwd=self.working_directory,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy()
        )

    def _execute_streaming(
        self,
        command: str,
        callback: Callable[[str], None],
        timeout: Optional[int]
    ) -> subprocess.CompletedProcess:
        """Execute command with streaming output.

        Args:
            command: Command to execute.
            callback: Callback for output lines.
            timeout: Timeout in seconds.

        Returns:
            CompletedProcess-like object.
        """
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=self.working_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy()
        )

        stdout_lines = []
        stderr_lines = []

        def read_output(pipe, lines_list, prefix=""):
            """Read output from pipe."""
            try:
                for line in iter(pipe.readline, ''):
                    if line:
                        lines_list.append(line)
                        callback(f"{prefix}{line.rstrip()}")
            finally:
                pipe.close()

        # Start threads to read stdout and stderr
        stdout_thread = threading.Thread(
            target=read_output,
            args=(process.stdout, stdout_lines, "")
        )
        stderr_thread = threading.Thread(
            target=read_output,
            args=(process.stderr, stderr_lines, "[stderr] ")
        )

        stdout_thread.start()
        stderr_thread.start()

        # Wait for process to complete
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            raise

        # Wait for threads to finish
        stdout_thread.join()
        stderr_thread.join()

        # Create result object
        result = type('CompletedProcess', (), {
            'returncode': returncode,
            'stdout': ''.join(stdout_lines),
            'stderr': ''.join(stderr_lines),
        })()

        return result

    def execute_multiple(
        self,
        commands: List[str],
        stop_on_error: bool = True,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> List[CommandResult]:
        """Execute multiple commands.

        Args:
            commands: List of commands to execute.
            stop_on_error: Whether to stop on first error.
            stream_callback: Optional callback for streaming output.

        Returns:
            List of CommandResult objects.
        """
        results = []

        for i, command in enumerate(commands):
            if stream_callback:
                stream_callback(f"\n[{i+1}/{len(commands)}] Executing: {command}")

            result = self.execute(command, stream_callback=stream_callback)
            results.append(result)

            if not result.success and stop_on_error:
                if stream_callback:
                    stream_callback(f"Stopping execution due to error in command: {command}")
                break

        return results

    def _add_to_history(self, result: CommandResult) -> None:
        """Add command result to history.

        Args:
            result: Command result to add.
        """
        self.command_history.append(result)

        # Trim history if needed
        if len(self.command_history) > self.max_history:
            self.command_history = self.command_history[-self.max_history:]

    def get_history(self, limit: Optional[int] = None) -> List[CommandResult]:
        """Get command history.

        Args:
            limit: Maximum number of results to return.

        Returns:
            List of CommandResult objects.
        """
        if limit:
            return self.command_history[-limit:]
        return self.command_history.copy()

    def clear_history(self) -> None:
        """Clear command history."""
        self.command_history.clear()

    def run_tests(self, test_command: Optional[str] = None) -> CommandResult:
        """Run project tests.

        Args:
            test_command: Custom test command. Auto-detects if None.

        Returns:
            CommandResult from test execution.
        """
        if test_command:
            return self.execute(test_command)

        # Auto-detect test command
        if (self.working_directory / 'package.json').exists():
            return self.execute('npm test')
        elif (self.working_directory / 'pytest.ini').exists() or \
             (self.working_directory / 'setup.py').exists():
            return self.execute('pytest')
        elif (self.working_directory / 'Cargo.toml').exists():
            return self.execute('cargo test')
        elif (self.working_directory / 'go.mod').exists():
            return self.execute('go test ./...')
        else:
            return CommandResult(
                command="auto-detect test",
                returncode=-1,
                stdout="",
                stderr="Could not auto-detect test command. Please specify manually.",
                duration=0.0
            )

    def run_build(self, build_command: Optional[str] = None) -> CommandResult:
        """Run project build.

        Args:
            build_command: Custom build command. Auto-detects if None.

        Returns:
            CommandResult from build execution.
        """
        if build_command:
            return self.execute(build_command)

        # Auto-detect build command
        if (self.working_directory / 'package.json').exists():
            return self.execute('npm run build')
        elif (self.working_directory / 'setup.py').exists():
            return self.execute('python setup.py build')
        elif (self.working_directory / 'Cargo.toml').exists():
            return self.execute('cargo build')
        elif (self.working_directory / 'go.mod').exists():
            return self.execute('go build ./...')
        elif (self.working_directory / 'Makefile').exists():
            return self.execute('make')
        else:
            return CommandResult(
                command="auto-detect build",
                returncode=-1,
                stdout="",
                stderr="Could not auto-detect build command. Please specify manually.",
                duration=0.0
            )

    def run_linter(self, linter_command: Optional[str] = None) -> CommandResult:
        """Run code linter.

        Args:
            linter_command: Custom linter command. Auto-detects if None.

        Returns:
            CommandResult from linter execution.
        """
        if linter_command:
            return self.execute(linter_command)

        # Auto-detect linter
        if (self.working_directory / 'package.json').exists():
            return self.execute('npm run lint')
        elif (self.working_directory / '.flake8').exists():
            return self.execute('flake8 .')
        elif (self.working_directory / 'pyproject.toml').exists():
            return self.execute('black --check .')
        else:
            return CommandResult(
                command="auto-detect linter",
                returncode=-1,
                stdout="",
                stderr="Could not auto-detect linter. Please specify manually.",
                duration=0.0
            )
