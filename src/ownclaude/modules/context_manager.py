"""Context manager for maintaining project and folder awareness."""

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import fnmatch

from loguru import logger


class ProjectContext:
    """Maintains context about the current project/folder structure."""

    # Common ignore patterns
    DEFAULT_IGNORE_PATTERNS = [
        ".git", ".svn", ".hg",
        "node_modules", "venv", "env", ".venv",
        "__pycache__", "*.pyc", ".pytest_cache",
        ".tox", ".eggs", "*.egg-info",
        "build", "dist", ".build",
        ".idea", ".vscode", ".vs",
        "*.min.js", "*.min.css",
    ]

    # Language file extensions
    LANGUAGE_EXTENSIONS = {
        'python': ['.py', '.pyx', '.pyi'],
        'javascript': ['.js', '.jsx', '.mjs'],
        'typescript': ['.ts', '.tsx'],
        'java': ['.java'],
        'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.h'],
        'c': ['.c', '.h'],
        'go': ['.go'],
        'rust': ['.rs'],
        'ruby': ['.rb'],
        'php': ['.php'],
        'html': ['.html', '.htm'],
        'css': ['.css', '.scss', '.sass'],
        'markdown': ['.md', '.markdown'],
        'json': ['.json'],
        'yaml': ['.yaml', '.yml'],
        'xml': ['.xml'],
        'shell': ['.sh', '.bash', '.zsh'],
    }

    def __init__(self, root_path: Optional[Path] = None):
        """Initialize project context.

        Args:
            root_path: Root path of the project. Defaults to current directory.
        """
        self.root_path = root_path or Path.cwd()
        self.file_tree: Dict[str, Any] = {}
        self.file_index: Dict[str, Path] = {}  # filename -> full path
        self.language_files: Dict[str, List[Path]] = defaultdict(list)
        self.project_type: Optional[str] = None
        self.important_files: List[Path] = []
        self.cached_summaries: Dict[Path, str] = {}
        self._initialized = False

    def initialize(self, max_depth: int = 5) -> None:
        """Scan and index the project structure.

        Args:
            max_depth: Maximum depth to scan.
        """
        logger.info(f"Initializing project context for: {self.root_path}")

        self.file_tree = self._build_tree(self.root_path, max_depth)
        self.project_type = self._detect_project_type()
        self.important_files = self._find_important_files()

        self._initialized = True
        logger.info(f"Project context initialized: {len(self.file_index)} files indexed")
        logger.info(f"Project type detected: {self.project_type or 'Unknown'}")

    def _build_tree(
        self,
        path: Path,
        max_depth: int,
        current_depth: int = 0
    ) -> Dict[str, Any]:
        """Build a tree structure of the project.

        Args:
            path: Path to scan.
            max_depth: Maximum depth to scan.
            current_depth: Current recursion depth.

        Returns:
            Tree structure dictionary.
        """
        if current_depth >= max_depth:
            return {}

        tree = {
            'type': 'directory' if path.is_dir() else 'file',
            'path': path,
            'name': path.name,
            'children': {}
        }

        if not path.is_dir():
            # Index file
            self.file_index[path.name] = path

            # Categorize by language
            ext = path.suffix.lower()
            for lang, extensions in self.LANGUAGE_EXTENSIONS.items():
                if ext in extensions:
                    self.language_files[lang].append(path)
                    break

            return tree

        try:
            for item in path.iterdir():
                # Skip ignored patterns
                if self._should_ignore(item):
                    continue

                tree['children'][item.name] = self._build_tree(
                    item,
                    max_depth,
                    current_depth + 1
                )
        except (PermissionError, OSError) as e:
            logger.warning(f"Cannot access {path}: {e}")

        return tree

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored.

        Args:
            path: Path to check.

        Returns:
            True if should be ignored.
        """
        name = path.name

        for pattern in self.DEFAULT_IGNORE_PATTERNS:
            if fnmatch.fnmatch(name, pattern):
                return True

        # Ignore hidden files/folders (except .gitignore, .env)
        if name.startswith('.') and name not in ['.gitignore', '.env', '.env.example']:
            return True

        return False

    def _detect_project_type(self) -> Optional[str]:
        """Detect the type of project.

        Returns:
            Project type string or None.
        """
        indicators = {
            'python': ['setup.py', 'pyproject.toml', 'requirements.txt', 'Pipfile'],
            'node': ['package.json', 'package-lock.json', 'yarn.lock'],
            'java': ['pom.xml', 'build.gradle', 'build.xml'],
            'rust': ['Cargo.toml', 'Cargo.lock'],
            'go': ['go.mod', 'go.sum'],
            'ruby': ['Gemfile', 'Rakefile'],
            'php': ['composer.json', 'composer.lock'],
            'dotnet': ['.csproj', '.sln', '.fsproj'],
        }

        for proj_type, files in indicators.items():
            for file in files:
                if (self.root_path / file).exists():
                    return proj_type

        # Fallback to most common language
        if self.language_files:
            return max(self.language_files.keys(), key=lambda k: len(self.language_files[k]))

        return None

    def _find_important_files(self) -> List[Path]:
        """Find important project files (README, config, etc.).

        Returns:
            List of important file paths.
        """
        important = []

        # Common important files
        patterns = [
            'README*', 'readme*',
            'LICENSE*', 'LICENCE*',
            'CONTRIBUTING*',
            '.gitignore',
            'Makefile',
            'Dockerfile',
            '.dockerignore',
            'docker-compose.yml',
            'config.*', 'settings.*',
            '.env.example',
        ]

        for pattern in patterns:
            matches = list(self.root_path.glob(pattern))
            important.extend([m for m in matches if m.is_file()])

        return important

    def get_project_summary(self) -> str:
        """Generate a summary of the project structure.

        Returns:
            Human-readable project summary.
        """
        if not self._initialized:
            self.initialize()

        lines = [
            f"Project: {self.root_path.name}",
            f"Location: {self.root_path}",
            f"Type: {self.project_type or 'Unknown'}",
            f"\nFile Statistics:",
            f"  Total files indexed: {len(self.file_index)}",
        ]

        # Language breakdown
        if self.language_files:
            lines.append("\nLanguages:")
            for lang, files in sorted(
                self.language_files.items(),
                key=lambda x: len(x[1]),
                reverse=True
            ):
                lines.append(f"  {lang.capitalize()}: {len(files)} files")

        # Important files
        if self.important_files:
            lines.append("\nImportant files:")
            for file in self.important_files[:10]:
                lines.append(f"  - {file.name}")

        return "\n".join(lines)

    def find_files(
        self,
        pattern: str,
        language: Optional[str] = None
    ) -> List[Path]:
        """Find files matching a pattern.

        Args:
            pattern: Glob pattern or filename.
            language: Optional language filter.

        Returns:
            List of matching file paths.
        """
        if not self._initialized:
            self.initialize()

        matches = []

        # Search in language-specific files
        if language:
            files_to_search = self.language_files.get(language, [])
        else:
            files_to_search = self.file_index.values()

        for file_path in files_to_search:
            if fnmatch.fnmatch(file_path.name, pattern):
                matches.append(file_path)
            elif pattern.lower() in file_path.name.lower():
                matches.append(file_path)

        return matches

    def get_file_context(self, file_path: Path) -> Dict[str, Any]:
        """Get contextual information about a file.

        Args:
            file_path: Path to the file.

        Returns:
            Dictionary with file context.
        """
        context = {
            'path': file_path,
            'name': file_path.name,
            'extension': file_path.suffix,
            'size': file_path.stat().st_size if file_path.exists() else 0,
            'relative_path': None,
            'language': None,
            'related_files': [],
        }

        # Get relative path
        try:
            context['relative_path'] = file_path.relative_to(self.root_path)
        except ValueError:
            context['relative_path'] = file_path

        # Detect language
        ext = file_path.suffix.lower()
        for lang, extensions in self.LANGUAGE_EXTENSIONS.items():
            if ext in extensions:
                context['language'] = lang
                break

        # Find related files (same name, different extension)
        stem = file_path.stem
        for indexed_file in self.file_index.values():
            if indexed_file.stem == stem and indexed_file != file_path:
                context['related_files'].append(indexed_file)

        return context

    def get_folder_structure(self, max_depth: int = 2) -> str:
        """Get a formatted folder structure.

        Args:
            max_depth: Maximum depth to display.

        Returns:
            Formatted tree string.
        """
        if not self._initialized:
            self.initialize()

        def _format_tree(node: Dict[str, Any], prefix: str = "", depth: int = 0) -> List[str]:
            if depth >= max_depth:
                return []

            lines = []

            if node['type'] == 'file':
                lines.append(f"{prefix}📄 {node['name']}")
            else:
                lines.append(f"{prefix}📁 {node['name']}/")

                children = node.get('children', {})
                sorted_children = sorted(
                    children.items(),
                    key=lambda x: (x[1]['type'] != 'directory', x[0])
                )

                for i, (name, child) in enumerate(sorted_children):
                    is_last = i == len(sorted_children) - 1
                    child_prefix = prefix + ("└── " if is_last else "├── ")
                    next_prefix = prefix + ("    " if is_last else "│   ")

                    lines.extend(_format_tree(child, child_prefix, depth + 1))

            return lines

        return "\n".join(_format_tree(self.file_tree))

    def analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Python file for functions, classes, imports.

        Args:
            file_path: Path to Python file.

        Returns:
            Analysis results.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)

            analysis = {
                'functions': [],
                'classes': [],
                'imports': [],
                'docstring': ast.get_docstring(tree),
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis['functions'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args],
                        'docstring': ast.get_docstring(node),
                    })
                elif isinstance(node, ast.ClassDef):
                    methods = [
                        n.name for n in node.body
                        if isinstance(n, ast.FunctionDef)
                    ]
                    analysis['classes'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'methods': methods,
                        'docstring': ast.get_docstring(node),
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            analysis['imports'].append(alias.name)
                    else:
                        module = node.module or ''
                        for alias in node.names:
                            analysis['imports'].append(f"{module}.{alias.name}")

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {e}")
            return {}

    def get_relevant_context(
        self,
        query: str,
        max_files: int = 10
    ) -> List[Dict[str, Any]]:
        """Get relevant files/context for a query.

        Args:
            query: Query string.
            max_files: Maximum files to return.

        Returns:
            List of relevant file contexts.
        """
        if not self._initialized:
            self.initialize()

        # Simple relevance scoring based on filename matching
        scored_files = []

        query_lower = query.lower()
        query_parts = query_lower.split()

        for file_path in self.file_index.values():
            score = 0
            file_lower = str(file_path).lower()

            # Exact filename match
            if query_lower in file_path.name.lower():
                score += 10

            # Partial matches
            for part in query_parts:
                if part in file_lower:
                    score += 1

            if score > 0:
                scored_files.append((score, file_path))

        # Sort by score and return top results
        scored_files.sort(reverse=True, key=lambda x: x[0])

        return [
            self.get_file_context(file_path)
            for score, file_path in scored_files[:max_files]
        ]


class ContextCache:
    """Cache for expensive context operations."""

    def __init__(self, max_size: int = 100):
        """Initialize context cache.

        Args:
            max_size: Maximum cache size.
        """
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size
        self.access_count: Dict[str, int] = defaultdict(int)

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None.
        """
        if key in self.cache:
            self.access_count[key] += 1
            return self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set item in cache.

        Args:
            key: Cache key.
            value: Value to cache.
        """
        if len(self.cache) >= self.max_size:
            # Evict least accessed item
            least_accessed = min(self.access_count.items(), key=lambda x: x[1])[0]
            del self.cache[least_accessed]
            del self.access_count[least_accessed]

        self.cache[key] = value
        self.access_count[key] = 0

    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        self.access_count.clear()
