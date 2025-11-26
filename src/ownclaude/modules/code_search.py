"""Code search and navigation tools for finding and analyzing code."""

import re
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from loguru import logger


@dataclass
class SearchMatch:
    """Represents a search match in code."""
    file_path: Path
    line_number: int
    line_content: str
    context_before: List[str]
    context_after: List[str]
    match_start: int
    match_end: int


@dataclass
class CodeDefinition:
    """Represents a code definition (function, class, etc.)."""
    name: str
    type: str  # 'function', 'class', 'method', 'variable'
    file_path: Path
    line_number: int
    end_line: Optional[int]
    signature: Optional[str]
    docstring: Optional[str]
    parent: Optional[str]  # For methods, the class name


class CodeSearch:
    """Advanced code search and navigation."""

    def __init__(self, root_path: Optional[Path] = None):
        """Initialize code search.

        Args:
            root_path: Root path to search in. Defaults to current directory.
        """
        self.root_path = root_path or Path.cwd()
        self.ignore_patterns = [
            '.git', '__pycache__', 'node_modules', 'venv', '.venv',
            'build', 'dist', '.tox', '.eggs', '*.pyc', '*.min.js'
        ]

    def grep(
        self,
        pattern: str,
        file_pattern: str = "*",
        case_sensitive: bool = False,
        whole_word: bool = False,
        context_lines: int = 2,
        max_results: int = 100
    ) -> List[SearchMatch]:
        """Search for pattern in files (similar to grep).

        Args:
            pattern: Regex pattern to search for.
            file_pattern: Glob pattern for files to search.
            case_sensitive: Whether search is case sensitive.
            whole_word: Whether to match whole words only.
            context_lines: Number of context lines before/after match.
            max_results: Maximum number of results to return.

        Returns:
            List of SearchMatch objects.
        """
        matches = []

        # Compile regex pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        if whole_word:
            pattern = r'\b' + pattern + r'\b'

        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return []

        # Find files to search
        files = self._find_files(file_pattern)

        for file_path in files:
            if len(matches) >= max_results:
                break

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                for i, line in enumerate(lines):
                    if len(matches) >= max_results:
                        break

                    match = regex.search(line)
                    if match:
                        # Get context lines
                        start_context = max(0, i - context_lines)
                        end_context = min(len(lines), i + context_lines + 1)

                        context_before = [
                            lines[j].rstrip()
                            for j in range(start_context, i)
                        ]
                        context_after = [
                            lines[j].rstrip()
                            for j in range(i + 1, end_context)
                        ]

                        matches.append(SearchMatch(
                            file_path=file_path,
                            line_number=i + 1,
                            line_content=line.rstrip(),
                            context_before=context_before,
                            context_after=context_after,
                            match_start=match.start(),
                            match_end=match.end()
                        ))

            except Exception as e:
                logger.debug(f"Error searching {file_path}: {e}")
                continue

        return matches

    def find_definition(
        self,
        name: str,
        def_type: Optional[str] = None
    ) -> List[CodeDefinition]:
        """Find definition of a function, class, or variable.

        Args:
            name: Name of the definition to find.
            def_type: Optional type filter ('function', 'class', 'method').

        Returns:
            List of CodeDefinition objects.
        """
        definitions = []

        # Search Python files
        python_files = self._find_files("*.py")

        for file_path in python_files:
            try:
                defs = self._find_python_definitions(file_path, name, def_type)
                definitions.extend(defs)
            except Exception as e:
                logger.debug(f"Error analyzing {file_path}: {e}")
                continue

        return definitions

    def _find_python_definitions(
        self,
        file_path: Path,
        name: str,
        def_type: Optional[str]
    ) -> List[CodeDefinition]:
        """Find definitions in a Python file.

        Args:
            file_path: Path to Python file.
            name: Name to search for.
            def_type: Optional type filter.

        Returns:
            List of CodeDefinition objects.
        """
        definitions = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name == name and (not def_type or def_type in ['function', 'method']):
                        # Determine if it's a method or function
                        is_method = self._is_method(node, tree)
                        parent_class = self._get_parent_class(node, tree) if is_method else None

                        # Build signature
                        args = []
                        for arg in node.args.args:
                            arg_str = arg.arg
                            if arg.annotation:
                                arg_str += f": {ast.unparse(arg.annotation)}"
                            args.append(arg_str)

                        signature = f"def {node.name}({', '.join(args)})"
                        if node.returns:
                            signature += f" -> {ast.unparse(node.returns)}"

                        definitions.append(CodeDefinition(
                            name=node.name,
                            type='method' if is_method else 'function',
                            file_path=file_path,
                            line_number=node.lineno,
                            end_line=node.end_lineno,
                            signature=signature,
                            docstring=ast.get_docstring(node),
                            parent=parent_class
                        ))

                elif isinstance(node, ast.ClassDef):
                    if node.name == name and (not def_type or def_type == 'class'):
                        # Build signature
                        bases = [ast.unparse(base) for base in node.bases]
                        signature = f"class {node.name}"
                        if bases:
                            signature += f"({', '.join(bases)})"

                        definitions.append(CodeDefinition(
                            name=node.name,
                            type='class',
                            file_path=file_path,
                            line_number=node.lineno,
                            end_line=node.end_lineno,
                            signature=signature,
                            docstring=ast.get_docstring(node),
                            parent=None
                        ))

        except SyntaxError:
            logger.debug(f"Syntax error in {file_path}")
        except Exception as e:
            logger.debug(f"Error parsing {file_path}: {e}")

        return definitions

    def _is_method(self, node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if a function is a method.

        Args:
            node: Function node.
            tree: AST tree.

        Returns:
            True if node is a method.
        """
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                if node in parent.body:
                    return True
        return False

    def _get_parent_class(self, node: ast.FunctionDef, tree: ast.AST) -> Optional[str]:
        """Get parent class name for a method.

        Args:
            node: Function node.
            tree: AST tree.

        Returns:
            Parent class name or None.
        """
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                if node in parent.body:
                    return parent.name
        return None

    def find_references(
        self,
        name: str,
        max_results: int = 50
    ) -> List[SearchMatch]:
        """Find all references to a name.

        Args:
            name: Name to find references to.
            max_results: Maximum results to return.

        Returns:
            List of SearchMatch objects.
        """
        # Use word boundary to match whole words only
        return self.grep(
            pattern=name,
            whole_word=True,
            context_lines=1,
            max_results=max_results
        )

    def find_imports(
        self,
        module_name: str
    ) -> List[SearchMatch]:
        """Find all imports of a module.

        Args:
            module_name: Module name to find imports for.

        Returns:
            List of SearchMatch objects.
        """
        # Pattern to match various import styles
        pattern = rf'(?:from\s+{module_name}|import\s+{module_name})'
        return self.grep(pattern, file_pattern="*.py", context_lines=0)

    def find_todos(self) -> List[SearchMatch]:
        """Find all TODO comments in code.

        Returns:
            List of SearchMatch objects.
        """
        pattern = r'#\s*TODO|//\s*TODO|/\*\s*TODO'
        return self.grep(pattern, case_sensitive=False, context_lines=1)

    def _find_files(self, pattern: str) -> List[Path]:
        """Find files matching a pattern.

        Args:
            pattern: Glob pattern.

        Returns:
            List of matching file paths.
        """
        files = []

        try:
            for file_path in self.root_path.rglob(pattern):
                if file_path.is_file() and not self._should_ignore(file_path):
                    files.append(file_path)
        except Exception as e:
            logger.error(f"Error finding files: {e}")

        return files

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored.

        Args:
            path: Path to check.

        Returns:
            True if should be ignored.
        """
        path_str = str(path)

        for pattern in self.ignore_patterns:
            if pattern in path_str:
                return True

        return False

    def get_file_symbols(self, file_path: Path) -> Dict[str, List[CodeDefinition]]:
        """Get all symbols (functions, classes) in a file.

        Args:
            file_path: Path to file.

        Returns:
            Dictionary of symbol types to definitions.
        """
        symbols: Dict[str, List[CodeDefinition]] = {
            'classes': [],
            'functions': [],
            'methods': []
        }

        if file_path.suffix != '.py':
            return symbols

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols['classes'].append(CodeDefinition(
                        name=node.name,
                        type='class',
                        file_path=file_path,
                        line_number=node.lineno,
                        end_line=node.end_lineno,
                        signature=f"class {node.name}",
                        docstring=ast.get_docstring(node),
                        parent=None
                    ))

                elif isinstance(node, ast.FunctionDef):
                    is_method = self._is_method(node, tree)
                    parent = self._get_parent_class(node, tree) if is_method else None

                    definition = CodeDefinition(
                        name=node.name,
                        type='method' if is_method else 'function',
                        file_path=file_path,
                        line_number=node.lineno,
                        end_line=node.end_lineno,
                        signature=f"def {node.name}",
                        docstring=ast.get_docstring(node),
                        parent=parent
                    )

                    if is_method:
                        symbols['methods'].append(definition)
                    else:
                        symbols['functions'].append(definition)

        except Exception as e:
            logger.debug(f"Error getting symbols from {file_path}: {e}")

        return symbols

    def search_by_type(
        self,
        pattern: str,
        language: str = "python"
    ) -> Dict[str, List[CodeDefinition]]:
        """Search for definitions by type.

        Args:
            pattern: Pattern to match (regex).
            language: Programming language.

        Returns:
            Dictionary of matches by type.
        """
        results: Dict[str, List[CodeDefinition]] = {
            'classes': [],
            'functions': [],
            'methods': []
        }

        if language != "python":
            logger.warning(f"Language {language} not yet supported")
            return results

        regex = re.compile(pattern, re.IGNORECASE)

        python_files = self._find_files("*.py")

        for file_path in python_files:
            symbols = self.get_file_symbols(file_path)

            for symbol_type, definitions in symbols.items():
                for definition in definitions:
                    if regex.search(definition.name):
                        results[symbol_type].append(definition)

        return results
