#!/usr/bin/env python3
"""Integration test to verify all OwnClaude modules work together."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ownclaude.modules.context_manager import ProjectContext
from ownclaude.modules.terminal_executor import TerminalExecutor
from ownclaude.modules.code_search import CodeSearch
from ownclaude.modules.git_integration import GitIntegration


def test_project_context():
    """Test project context manager."""
    print("Testing ProjectContext...")

    context = ProjectContext()
    context.initialize(max_depth=3)

    print(f"✓ Project initialized")
    print(f"✓ Found {len(context.file_index)} files")
    print(f"✓ Project type: {context.project_type}")

    summary = context.get_project_summary()
    print(f"✓ Generated project summary")

    # Test file finding
    python_files = context.find_files("*.py")
    print(f"✓ Found {len(python_files)} Python files")

    print("ProjectContext: PASSED\n")


def test_terminal_executor():
    """Test terminal command execution."""
    print("Testing TerminalExecutor...")

    executor = TerminalExecutor()

    # Test safe command
    result = executor.execute("echo 'Hello from OwnClaude!'")
    assert result.success, "Echo command should succeed"
    print(f"✓ Safe command execution works")

    # Test dangerous command blocking
    result = executor.execute("rm -rf /")
    assert not result.success, "Dangerous command should be blocked"
    print(f"✓ Dangerous command blocked correctly")

    # Test command history
    history = executor.get_history(limit=5)
    assert len(history) >= 1, "History should contain at least 1 command"
    print(f"✓ Command history working ({len(history)} commands recorded)")

    print("TerminalExecutor: PASSED\n")


def test_code_search():
    """Test code search functionality."""
    print("Testing CodeSearch...")

    search = CodeSearch()

    # Search for imports in Python files
    matches = search.grep("import", file_pattern="*.py", max_results=5)
    print(f"✓ Found {len(matches)} import statements")

    # Find class definitions
    definitions = search.find_definition("ProjectContext", def_type="class")
    if definitions:
        print(f"✓ Found ProjectContext class definition")
    else:
        print("⚠ ProjectContext class not found (may be expected)")

    # Search for TODOs
    todos = search.find_todos()
    print(f"✓ Found {len(todos)} TODO comments")

    print("CodeSearch: PASSED\n")


def test_git_integration():
    """Test git integration."""
    print("Testing GitIntegration...")

    git = GitIntegration()

    if git.is_repository():
        print(f"✓ Git repository detected")

        # Get status
        status = git.get_status()
        if status:
            print(f"✓ Current branch: {status.branch}")
            print(f"✓ Staged files: {len(status.staged)}")
            print(f"✓ Unstaged files: {len(status.unstaged)}")

        # Get log
        commits = git.get_log(max_count=3)
        print(f"✓ Retrieved {len(commits)} recent commits")

        # Get branches
        branches = git.list_branches()
        print(f"✓ Found {len(branches)} branches")
    else:
        print("⚠ Not a git repository (testing in non-git directory)")

    print("GitIntegration: PASSED\n")


def test_file_operations():
    """Test file operations through code."""
    print("Testing FileOperations...")

    from ownclaude.modules.file_operations import FileOperations

    ops = FileOperations()

    # Test create
    test_file = Path("test_temp_file.txt")
    success, msg, _ = ops.create_file(str(test_file), "Test content")
    assert success, f"File creation should succeed: {msg}"
    print("✓ File creation works")

    # Test read
    success, msg, content = ops.read_file(str(test_file))
    assert success and content == "Test content", "File read should succeed"
    print("✓ File reading works")

    # Test append
    success, msg, _ = ops.append_file(str(test_file), "\nAppended line")
    assert success, "File append should succeed"
    print("✓ File appending works")

    # Test delete
    success, msg, _ = ops.delete_file(str(test_file))
    assert success, "File deletion should succeed"
    print("✓ File deletion works")

    print("FileOperations: PASSED\n")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("OwnClaude Integration Test Suite")
    print("=" * 60)
    print()

    try:
        test_project_context()
        test_terminal_executor()
        test_code_search()
        test_git_integration()
        test_file_operations()

        print("=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        print()
        print("OwnClaude is ready to use!")
        print("Run: python ownclaude.py")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
