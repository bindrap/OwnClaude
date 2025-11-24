"""File operations module for managing files and directories."""

import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from loguru import logger


class FileOperations:
    """Handles file and directory operations."""

    def __init__(self):
        """Initialize file operations handler."""
        pass

    def create_file(
        self,
        file_path: str,
        content: str = "",
        overwrite: bool = False
    ) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Create a new file.

        Args:
            file_path: Path to the file to create.
            content: Content to write to the file.
            overwrite: Whether to overwrite if file exists.

        Returns:
            Tuple of (success, message, rollback_info).
        """
        path = Path(file_path)

        try:
            # Check if file exists
            if path.exists() and not overwrite:
                return False, f"File already exists: {file_path}", None

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            path.write_text(content, encoding='utf-8')

            logger.info(f"Created file: {file_path}")
            rollback_info = {"path": str(path)}
            return True, f"Created file: {file_path}", rollback_info

        except Exception as e:
            logger.error(f"Failed to create file {file_path}: {e}")
            return False, str(e), None

    def read_file(self, file_path: str) -> tuple[bool, str, Optional[str]]:
        """Read content from a file.

        Args:
            file_path: Path to the file to read.

        Returns:
            Tuple of (success, message, content).
        """
        path = Path(file_path)

        try:
            if not path.exists():
                return False, f"File not found: {file_path}", None

            if not path.is_file():
                return False, f"Not a file: {file_path}", None

            content = path.read_text(encoding='utf-8')
            return True, f"Read {len(content)} characters from {file_path}", content

        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return False, str(e), None

    def modify_file(
        self,
        file_path: str,
        content: str
    ) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Modify an existing file.

        Args:
            file_path: Path to the file to modify.
            content: New content for the file.

        Returns:
            Tuple of (success, message, rollback_info).
        """
        path = Path(file_path)

        try:
            if not path.exists():
                return False, f"File not found: {file_path}", None

            # Save original content for rollback
            original_content = path.read_text(encoding='utf-8')

            # Write new content
            path.write_text(content, encoding='utf-8')

            logger.info(f"Modified file: {file_path}")
            rollback_info = {
                "path": str(path),
                "original_content": original_content
            }
            return True, f"Modified file: {file_path}", rollback_info

        except Exception as e:
            logger.error(f"Failed to modify file {file_path}: {e}")
            return False, str(e), None

    def append_file(
        self,
        file_path: str,
        content: str
    ) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Append content to an existing file (creates if missing).

        Args:
            file_path: Path to the file to append to.
            content: Content to append.

        Returns:
            Tuple of (success, message, rollback_info).
        """
        path = Path(file_path)

        try:
            original_content = ""
            if path.exists():
                original_content = path.read_text(encoding='utf-8')
            else:
                path.parent.mkdir(parents=True, exist_ok=True)

            with path.open("a", encoding="utf-8") as fh:
                fh.write(content)

            logger.info(f"Appended to file: {file_path}")
            rollback_info = {
                "path": str(path),
                "original_content": original_content
            }
            return True, f"Appended content to {file_path}", rollback_info

        except Exception as e:
            logger.error(f"Failed to append file {file_path}: {e}")
            return False, str(e), None

    def delete_file(self, file_path: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Delete a file.

        Args:
            file_path: Path to the file to delete.

        Returns:
            Tuple of (success, message, rollback_info).
        """
        path = Path(file_path)

        try:
            if not path.exists():
                return False, f"File not found: {file_path}", None

            if not path.is_file():
                return False, f"Not a file: {file_path}", None

            # Save content for rollback
            content = path.read_text(encoding='utf-8')

            # Delete file
            path.unlink()

            logger.info(f"Deleted file: {file_path}")
            rollback_info = {
                "path": str(path),
                "content": content
            }
            return True, f"Deleted file: {file_path}", rollback_info

        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False, str(e), None

    def create_directory(self, dir_path: str) -> tuple[bool, str]:
        """Create a directory.

        Args:
            dir_path: Path to the directory to create.

        Returns:
            Tuple of (success, message).
        """
        path = Path(dir_path)

        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
            return True, f"Created directory: {dir_path}"

        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            return False, str(e)

    def delete_directory(
        self,
        dir_path: str,
        recursive: bool = False
    ) -> tuple[bool, str]:
        """Delete a directory.

        Args:
            dir_path: Path to the directory to delete.
            recursive: Whether to delete recursively (non-empty directories).

        Returns:
            Tuple of (success, message).
        """
        path = Path(dir_path)

        try:
            if not path.exists():
                return False, f"Directory not found: {dir_path}"

            if not path.is_dir():
                return False, f"Not a directory: {dir_path}"

            if recursive:
                shutil.rmtree(path)
            else:
                path.rmdir()  # Only works for empty directories

            logger.info(f"Deleted directory: {dir_path}")
            return True, f"Deleted directory: {dir_path}"

        except Exception as e:
            logger.error(f"Failed to delete directory {dir_path}: {e}")
            return False, str(e)

    def list_directory(self, dir_path: str = ".") -> tuple[bool, str, Optional[List[Dict[str, Any]]]]:
        """List contents of a directory.

        Args:
            dir_path: Path to the directory to list.

        Returns:
            Tuple of (success, message, contents).
        """
        path = Path(dir_path)

        try:
            if not path.exists():
                return False, f"Directory not found: {dir_path}", None

            if not path.is_dir():
                return False, f"Not a directory: {dir_path}", None

            contents = []
            for item in path.iterdir():
                stat = item.stat()
                contents.append({
                    'name': item.name,
                    'path': str(item),
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': stat.st_size if item.is_file() else 0,
                    'modified': stat.st_mtime
                })

            contents.sort(key=lambda x: (x['type'] != 'directory', x['name']))
            return True, f"Listed {len(contents)} items in {dir_path}", contents

        except Exception as e:
            logger.error(f"Failed to list directory {dir_path}: {e}")
            return False, str(e), None

    def search_files(
        self,
        directory: str,
        pattern: str,
        recursive: bool = True
    ) -> tuple[bool, str, Optional[List[str]]]:
        """Search for files matching a pattern.

        Args:
            directory: Directory to search in.
            pattern: Glob pattern to match (e.g., "*.txt", "**/*.py").
            recursive: Whether to search recursively.

        Returns:
            Tuple of (success, message, matching_files).
        """
        path = Path(directory)

        try:
            if not path.exists():
                return False, f"Directory not found: {directory}", None

            if not path.is_dir():
                return False, f"Not a directory: {directory}", None

            if recursive and not pattern.startswith("**"):
                pattern = f"**/{pattern}"

            matches = [str(p) for p in path.glob(pattern)]
            matches.sort()

            return True, f"Found {len(matches)} matching file(s)", matches

        except Exception as e:
            logger.error(f"Failed to search files in {directory}: {e}")
            return False, str(e), None

    def copy_file(
        self,
        source: str,
        destination: str,
        overwrite: bool = False
    ) -> tuple[bool, str]:
        """Copy a file.

        Args:
            source: Source file path.
            destination: Destination file path.
            overwrite: Whether to overwrite if destination exists.

        Returns:
            Tuple of (success, message).
        """
        src = Path(source)
        dst = Path(destination)

        try:
            if not src.exists():
                return False, f"Source file not found: {source}"

            if not src.is_file():
                return False, f"Source is not a file: {source}"

            if dst.exists() and not overwrite:
                return False, f"Destination already exists: {destination}"

            # Create destination directory if needed
            dst.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(src, dst)
            logger.info(f"Copied {source} to {destination}")
            return True, f"Copied {source} to {destination}"

        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            return False, str(e)

    def move_file(
        self,
        source: str,
        destination: str,
        overwrite: bool = False
    ) -> tuple[bool, str]:
        """Move a file.

        Args:
            source: Source file path.
            destination: Destination file path.
            overwrite: Whether to overwrite if destination exists.

        Returns:
            Tuple of (success, message).
        """
        src = Path(source)
        dst = Path(destination)

        try:
            if not src.exists():
                return False, f"Source file not found: {source}"

            if dst.exists() and not overwrite:
                return False, f"Destination already exists: {destination}"

            # Create destination directory if needed
            dst.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(src), str(dst))
            logger.info(f"Moved {source} to {destination}")
            return True, f"Moved {source} to {destination}"

        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            return False, str(e)

    def get_file_info(self, file_path: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Get information about a file.

        Args:
            file_path: Path to the file.

        Returns:
            Tuple of (success, message, file_info).
        """
        path = Path(file_path)

        try:
            if not path.exists():
                return False, f"File not found: {file_path}", None

            stat = path.stat()
            info = {
                'name': path.name,
                'path': str(path.absolute()),
                'type': 'directory' if path.is_dir() else 'file',
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'accessed': stat.st_atime,
            }

            if path.is_file():
                info['extension'] = path.suffix

            return True, "File info retrieved", info

        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return False, str(e), None
