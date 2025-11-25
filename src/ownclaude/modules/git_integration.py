"""Git integration for version control operations."""

import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from loguru import logger


@dataclass
class GitCommit:
    """Represents a git commit."""
    hash: str
    author: str
    date: datetime
    message: str
    files_changed: int


@dataclass
class GitStatus:
    """Represents git repository status."""
    branch: str
    staged: List[str]
    unstaged: List[str]
    untracked: List[str]
    ahead: int
    behind: int


class GitIntegration:
    """Git version control integration."""

    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize git integration.

        Args:
            repo_path: Path to git repository. Defaults to current directory.
        """
        self.repo_path = repo_path or Path.cwd()
        self._is_repo = self._check_is_repo()

    def _check_is_repo(self) -> bool:
        """Check if current directory is a git repository.

        Returns:
            True if is a git repo.
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def is_repository(self) -> bool:
        """Check if this is a git repository.

        Returns:
            True if is a git repository.
        """
        return self._is_repo

    def get_status(self) -> Optional[GitStatus]:
        """Get current git status.

        Returns:
            GitStatus object or None if not a repo.
        """
        if not self._is_repo:
            return None

        try:
            # Get branch name
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            branch = branch_result.stdout.strip()

            # Get status
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            staged = []
            unstaged = []
            untracked = []

            for line in status_result.stdout.splitlines():
                if not line:
                    continue

                status_code = line[:2]
                file_path = line[3:]

                if status_code[0] != ' ' and status_code[0] != '?':
                    staged.append(file_path)
                if status_code[1] != ' ':
                    unstaged.append(file_path)
                if status_code == '??':
                    untracked.append(file_path)

            # Get ahead/behind info
            ahead, behind = self._get_ahead_behind()

            return GitStatus(
                branch=branch,
                staged=staged,
                unstaged=unstaged,
                untracked=untracked,
                ahead=ahead,
                behind=behind
            )

        except Exception as e:
            logger.error(f"Failed to get git status: {e}")
            return None

    def _get_ahead_behind(self) -> Tuple[int, int]:
        """Get ahead/behind commit count.

        Returns:
            Tuple of (ahead, behind).
        """
        try:
            result = subprocess.run(
                ['git', 'rev-list', '--left-right', '--count', 'HEAD...@{upstream}'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                parts = result.stdout.strip().split()
                return int(parts[0]), int(parts[1])
        except Exception:
            pass

        return 0, 0

    def get_diff(self, staged: bool = False) -> str:
        """Get git diff.

        Args:
            staged: Whether to get staged diff.

        Returns:
            Diff output.
        """
        if not self._is_repo:
            return ""

        try:
            cmd = ['git', 'diff']
            if staged:
                cmd.append('--cached')

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            return result.stdout

        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
            return ""

    def get_log(self, max_count: int = 10) -> List[GitCommit]:
        """Get git log.

        Args:
            max_count: Maximum number of commits to retrieve.

        Returns:
            List of GitCommit objects.
        """
        if not self._is_repo:
            return []

        try:
            result = subprocess.run(
                [
                    'git', 'log',
                    f'-{max_count}',
                    '--pretty=format:%H|%an|%at|%s',
                    '--shortstat'
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            commits = []
            lines = result.stdout.splitlines()
            i = 0

            while i < len(lines):
                line = lines[i].strip()
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        commit_hash = parts[0]
                        author = parts[1]
                        timestamp = int(parts[2])
                        message = parts[3]

                        # Look for file changes in next line
                        files_changed = 0
                        if i + 1 < len(lines) and 'file' in lines[i + 1]:
                            # Parse "X files changed" from stat line
                            stat_line = lines[i + 1]
                            if 'file' in stat_line:
                                try:
                                    files_changed = int(stat_line.split()[0])
                                except (ValueError, IndexError):
                                    pass
                            i += 1

                        commits.append(GitCommit(
                            hash=commit_hash,
                            author=author,
                            date=datetime.fromtimestamp(timestamp),
                            message=message,
                            files_changed=files_changed
                        ))

                i += 1

            return commits

        except Exception as e:
            logger.error(f"Failed to get log: {e}")
            return []

    def stage_files(self, files: List[str]) -> Tuple[bool, str]:
        """Stage files for commit.

        Args:
            files: List of file paths to stage.

        Returns:
            Tuple of (success, message).
        """
        if not self._is_repo:
            return False, "Not a git repository"

        try:
            result = subprocess.run(
                ['git', 'add'] + files,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, f"Staged {len(files)} file(s)"
            else:
                return False, result.stderr

        except Exception as e:
            logger.error(f"Failed to stage files: {e}")
            return False, str(e)

    def unstage_files(self, files: List[str]) -> Tuple[bool, str]:
        """Unstage files.

        Args:
            files: List of file paths to unstage.

        Returns:
            Tuple of (success, message).
        """
        if not self._is_repo:
            return False, "Not a git repository"

        try:
            result = subprocess.run(
                ['git', 'reset', 'HEAD'] + files,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, f"Unstaged {len(files)} file(s)"
            else:
                return False, result.stderr

        except Exception as e:
            logger.error(f"Failed to unstage files: {e}")
            return False, str(e)

    def commit(self, message: str) -> Tuple[bool, str]:
        """Create a commit.

        Args:
            message: Commit message.

        Returns:
            Tuple of (success, message).
        """
        if not self._is_repo:
            return False, "Not a git repository"

        try:
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, "Commit created successfully"
            else:
                return False, result.stderr

        except Exception as e:
            logger.error(f"Failed to commit: {e}")
            return False, str(e)

    def create_branch(self, branch_name: str, checkout: bool = True) -> Tuple[bool, str]:
        """Create a new branch.

        Args:
            branch_name: Name of new branch.
            checkout: Whether to checkout the new branch.

        Returns:
            Tuple of (success, message).
        """
        if not self._is_repo:
            return False, "Not a git repository"

        try:
            cmd = ['git', 'branch', branch_name]
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return False, result.stderr

            if checkout:
                checkout_result = subprocess.run(
                    ['git', 'checkout', branch_name],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if checkout_result.returncode != 0:
                    return False, checkout_result.stderr

            return True, f"Branch '{branch_name}' created" + (" and checked out" if checkout else "")

        except Exception as e:
            logger.error(f"Failed to create branch: {e}")
            return False, str(e)

    def checkout_branch(self, branch_name: str) -> Tuple[bool, str]:
        """Checkout a branch.

        Args:
            branch_name: Name of branch to checkout.

        Returns:
            Tuple of (success, message).
        """
        if not self._is_repo:
            return False, "Not a git repository"

        try:
            result = subprocess.run(
                ['git', 'checkout', branch_name],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, f"Switched to branch '{branch_name}'"
            else:
                return False, result.stderr

        except Exception as e:
            logger.error(f"Failed to checkout branch: {e}")
            return False, str(e)

    def list_branches(self) -> List[str]:
        """List all branches.

        Returns:
            List of branch names.
        """
        if not self._is_repo:
            return []

        try:
            result = subprocess.run(
                ['git', 'branch', '--list'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            branches = []
            for line in result.stdout.splitlines():
                # Remove * for current branch and whitespace
                branch = line.strip().lstrip('* ')
                if branch:
                    branches.append(branch)

            return branches

        except Exception as e:
            logger.error(f"Failed to list branches: {e}")
            return []

    def get_changed_files(self, commit1: str = "HEAD", commit2: Optional[str] = None) -> List[str]:
        """Get list of changed files between commits.

        Args:
            commit1: First commit (default HEAD).
            commit2: Second commit (default None for working directory).

        Returns:
            List of changed file paths.
        """
        if not self._is_repo:
            return []

        try:
            cmd = ['git', 'diff', '--name-only', commit1]
            if commit2:
                cmd.append(commit2)

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            return [line.strip() for line in result.stdout.splitlines() if line.strip()]

        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return []

    def get_file_history(self, file_path: str, max_count: int = 10) -> List[GitCommit]:
        """Get commit history for a specific file.

        Args:
            file_path: Path to file.
            max_count: Maximum number of commits.

        Returns:
            List of GitCommit objects.
        """
        if not self._is_repo:
            return []

        try:
            result = subprocess.run(
                [
                    'git', 'log',
                    f'-{max_count}',
                    '--pretty=format:%H|%an|%at|%s',
                    '--', file_path
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            commits = []
            for line in result.stdout.splitlines():
                parts = line.split('|')
                if len(parts) >= 4:
                    commits.append(GitCommit(
                        hash=parts[0],
                        author=parts[1],
                        date=datetime.fromtimestamp(int(parts[2])),
                        message=parts[3],
                        files_changed=1
                    ))

            return commits

        except Exception as e:
            logger.error(f"Failed to get file history: {e}")
            return []
