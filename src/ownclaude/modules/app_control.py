"""Application control module for opening and managing applications."""

import os
import platform
import subprocess
from pathlib import Path
from typing import List, Optional

import psutil
from loguru import logger


class AppController:
    """Controls application launching and management."""

    def __init__(self):
        """Initialize application controller."""
        self.system = platform.system()
        self.running_apps = {}

    def open_application(self, app_name: str) -> tuple[bool, str]:
        """Open an application by name.

        Args:
            app_name: Name or path of the application to open.

        Returns:
            Tuple of (success, message).
        """
        try:
            if self.system == "Windows":
                return self._open_windows(app_name)
            elif self.system == "Darwin":  # macOS
                return self._open_macos(app_name)
            elif self.system == "Linux":
                return self._open_linux(app_name)
            else:
                return False, f"Unsupported platform: {self.system}"
        except Exception as e:
            logger.error(f"Failed to open {app_name}: {e}")
            return False, str(e)

    def _open_windows(self, app_name: str) -> tuple[bool, str]:
        """Open application on Windows.

        Args:
            app_name: Application name or path.

        Returns:
            Tuple of (success, message).
        """
        # Common Windows applications
        app_mappings = {
            "vscode": "code",
            "vs code": "code",
            "visual studio code": "code",
            "code": "code",
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "excel": "excel.exe",
            "word": "winword.exe",
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
        }

        app_to_open = app_mappings.get(app_name.lower(), app_name)

        # Special handling for VS Code to find the actual executable if "code" isn't on PATH
        if app_to_open.lower() == "code":
            candidates = [
                Path(os.environ.get("ProgramFiles", "")) / "Microsoft VS Code" / "Code.exe",
                Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft VS Code" / "Code.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe",
            ]
            for candidate in candidates:
                if candidate.is_file():
                    app_to_open = str(candidate)
                    break

        try:
            subprocess.Popen(app_to_open, shell=True)
            return True, f"Opened {app_name}"
        except Exception as e:
            return False, f"Failed to open {app_name}: {e}"

    def _open_macos(self, app_name: str) -> tuple[bool, str]:
        """Open application on macOS.

        Args:
            app_name: Application name or path.

        Returns:
            Tuple of (success, message).
        """
        # Common macOS applications
        app_mappings = {
            "safari": "Safari",
            "chrome": "Google Chrome",
            "firefox": "Firefox",
            "mail": "Mail",
            "notes": "Notes",
            "calculator": "Calculator",
            "terminal": "Terminal",
            "finder": "Finder",
            "excel": "Microsoft Excel",
            "word": "Microsoft Word",
        }

        app_to_open = app_mappings.get(app_name.lower(), app_name)

        try:
            subprocess.Popen(["open", "-a", app_to_open])
            return True, f"Opened {app_name}"
        except Exception as e:
            return False, f"Failed to open {app_name}: {e}"

    def _open_linux(self, app_name: str) -> tuple[bool, str]:
        """Open application on Linux.

        Args:
            app_name: Application name or path.

        Returns:
            Tuple of (success, message).
        """
        # Common Linux applications
        app_mappings = {
            "browser": "xdg-open http://",
            "chrome": "google-chrome",
            "firefox": "firefox",
            "terminal": "gnome-terminal",
            "files": "nautilus",
            "calculator": "gnome-calculator",
            "text": "gedit",
        }

        app_to_open = app_mappings.get(app_name.lower(), app_name)

        try:
            subprocess.Popen([app_to_open], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, f"Opened {app_name}"
        except Exception as e:
            return False, f"Failed to open {app_name}: {e}"

    def close_application(self, app_name: str, force: bool = False) -> tuple[bool, str]:
        """Close an application by name.

        Args:
            app_name: Name of the application to close.
            force: Whether to force close the application.

        Returns:
            Tuple of (success, message).
        """
        try:
            closed_count = 0
            app_name_lower = app_name.lower()

            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name'].lower()
                    if app_name_lower in proc_name:
                        if force:
                            proc.kill()
                        else:
                            proc.terminate()
                        closed_count += 1
                        logger.info(f"Closed process: {proc.info['name']} (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if closed_count > 0:
                return True, f"Closed {closed_count} instance(s) of {app_name}"
            else:
                return False, f"No running instances of {app_name} found"

        except Exception as e:
            logger.error(f"Failed to close {app_name}: {e}")
            return False, str(e)

    def list_running_applications(self) -> List[dict]:
        """List all running applications.

        Returns:
            List of running application info.
        """
        apps = []
        seen_names = set()

        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                info = proc.info
                name = info['name']

                # Skip system processes and duplicates
                if name and name not in seen_names:
                    apps.append({
                        'name': name,
                        'pid': info['pid'],
                        'memory_mb': info['memory_info'].rss / (1024 * 1024)
                    })
                    seen_names.add(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return sorted(apps, key=lambda x: x['memory_mb'], reverse=True)

    def is_running(self, app_name: str) -> bool:
        """Check if an application is running.

        Args:
            app_name: Name of the application to check.

        Returns:
            True if running, False otherwise.
        """
        app_name_lower = app_name.lower()

        for proc in psutil.process_iter(['name']):
            try:
                if app_name_lower in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return False

    def open_url(self, url: str) -> tuple[bool, str]:
        """Open a URL in the default browser.

        Args:
            url: URL to open.

        Returns:
            Tuple of (success, message).
        """
        import webbrowser

        try:
            webbrowser.open(url)
            return True, f"Opened {url} in default browser"
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            return False, str(e)

    def open_file_with_default_app(self, file_path: str) -> tuple[bool, str]:
        """Open a file with its default application.

        Args:
            file_path: Path to the file to open.

        Returns:
            Tuple of (success, message).
        """
        path = Path(file_path)

        if not path.exists():
            return False, f"File not found: {file_path}"

        try:
            if self.system == "Windows":
                subprocess.Popen(["start", "", str(path)], shell=True)
            elif self.system == "Darwin":
                subprocess.Popen(["open", str(path)])
            elif self.system == "Linux":
                subprocess.Popen(["xdg-open", str(path)])

            return True, f"Opened {file_path} with default application"
        except Exception as e:
            logger.error(f"Failed to open file {file_path}: {e}")
            return False, str(e)
