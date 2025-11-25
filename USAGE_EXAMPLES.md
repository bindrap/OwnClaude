# OwnClaude Usage Examples

This guide shows you how to use OwnClaude's powerful features to control your computer and work with code.

## Table of Contents
1. [Basic File Operations](#basic-file-operations)
2. [Application Control](#application-control)
3. [Code Navigation](#code-navigation)
4. [Terminal Commands](#terminal-commands)
5. [Git Operations](#git-operations)
6. [Project Analysis](#project-analysis)
7. [Testing and Building](#testing-and-building)

## Basic File Operations

### Creating Files
```
You: create a Python script called calculator.py with basic add and subtract functions

OwnClaude: Creates calculator.py with functions
```

### Reading Files
```
You: show me what's in calculator.py

OwnClaude: Displays file contents
```

### Modifying Files
```
You: add a multiply function to calculator.py

OwnClaude: Updates the file with a new multiply function
```

### Searching Files
```
You: find all Python files in this directory

OwnClaude: Lists all .py files
```

## Application Control

### Opening Applications
```
You: open my browser
You: launch calculator
You: open excel
```

### Opening Files with Default Apps
```
You: open report.pdf
You: open presentation.pptx
```

### Closing Applications
```
You: close all browser windows
You: close notepad
```

## Code Navigation

### Searching Code
```
You: search for "def calculate" in Python files

OwnClaude: Shows all matches with file locations and line numbers
```

### Finding Definitions
```
You: find the definition of the UserAuth class

OwnClaude: Shows file, line number, and class signature
```

### Finding Function Definitions
```
You: where is the process_data function defined?

OwnClaude: Locates and shows the function definition
```

### Code Analysis
```
You: analyze the main.py file

OwnClaude: Shows classes, functions, imports, and docstrings
```

## Terminal Commands

### Running Commands
```
You: run 'ls -la' to see all files

OwnClaude: Executes command and shows output
```

### Checking Python Version
```
You: what version of Python is installed?

OwnClaude: Runs 'python --version' and shows result
```

### Installing Packages
```
You: install the requests package with pip

OwnClaude: Runs 'pip install requests'
```

### Safe Command Execution
OwnClaude has safety checks that prevent dangerous commands like:
- `rm -rf /` (recursive deletion)
- `sudo` commands (require manual execution)
- Format commands
- Fork bombs

## Git Operations

### Checking Repository Status
```
You: what's the git status?

OwnClaude: Shows current branch, staged/unstaged files, and untracked files
```

### Viewing Changes
```
You: show me the git diff

OwnClaude: Displays uncommitted changes
```

### Staging Files
```
You: stage all Python files

OwnClaude: Adds .py files to staging area
```

### Creating Commits
```
You: commit the changes with message "Add new feature"

OwnClaude: Creates a commit with the message
```

### Viewing Commit History
```
You: show me the last 5 commits

OwnClaude: Displays recent commit history
```

### Branch Operations
```
You: create a new branch called feature-auth
You: switch to the main branch
You: list all branches
```

## Project Analysis

### Getting Project Summary
```
You: give me a summary of this project

OwnClaude: Shows:
- Project type (Python, Node.js, etc.)
- File statistics
- Language breakdown
- Important files (README, config, etc.)
```

### Understanding Project Structure
```
You: what's the folder structure?

OwnClaude: Displays a tree view of directories and files
```

### Finding Related Files
```
You: find all test files

OwnClaude: Locates files matching test patterns
```

## Testing and Building

### Running Tests
```
You: run the tests

OwnClaude: Auto-detects and runs test suite (pytest, npm test, etc.)
```

### Running Specific Tests
```
You: run tests with 'pytest tests/test_auth.py'

OwnClaude: Runs the specified test file
```

### Building Project
```
You: build the project

OwnClaude: Auto-detects and runs build command
```

### Running Linter
```
You: check code style

OwnClaude: Runs linter (flake8, black, eslint, etc.)
```

## Advanced Examples

### Complex Workflow
```
You: I want to create a new feature branch, add a function, and run tests

OwnClaude:
1. Creates branch 'feature-new'
2. Adds the requested function
3. Runs tests to verify
4. Reports results
```

### Code Review
```
You: review the code I just wrote

OwnClaude: Analyzes recent code for:
- Best practices
- Security issues
- Performance concerns
- Error handling
```

### Debugging Help
```
You: diagnose why my tests are failing

OwnClaude:
1. Runs tests
2. Analyzes error messages
3. Suggests fixes
```

### Project Setup
```
You: help me set up a new Python project with a virtual environment

OwnClaude:
1. Creates project directory
2. Initializes virtual environment
3. Creates requirements.txt
4. Sets up basic project structure
```

## Special Commands

### Getting Help
```
You: help
```
Shows all available commands and features

### Viewing History
```
You: history
```
Shows recent operations

### Checking Status
```
You: status
```
Shows system permissions and settings

### Viewing Memory
```
You: memory
```
Shows conversation context

### Task Planning
```
You: plan
```
Shows current task plan

Press `F2` to toggle task plan preview on/off

### Clear Screen
```
You: clear
```
Clears the terminal

### Exit
```
You: exit
You: quit
```
Exits OwnClaude

## Tips for Effective Use

1. **Be Specific**: The more specific your request, the better OwnClaude can help
   - Good: "create a Python file called utils.py with a function to parse JSON"
   - Less good: "make a file"

2. **Use Context**: OwnClaude remembers conversation context
   - "create a file called test.py"
   - "now add a function to it" (OwnClaude knows which file)

3. **Leverage Auto-detection**: OwnClaude can auto-detect:
   - Project type (Python, Node.js, etc.)
   - Test commands
   - Build commands
   - Linter configuration

4. **Safety First**: OwnClaude has built-in safety features
   - Confirmation for destructive operations
   - Command validation
   - Rollback capabilities

5. **Multi-step Tasks**: Break complex tasks into steps or let OwnClaude plan them
   - "I need to refactor this module, add tests, and update docs"
   - OwnClaude will create a plan and execute step by step

## Troubleshooting

### Command Not Working
- Check permissions in config.json
- Verify Ollama is running: `ollama serve`
- Check logs in logs/ownclaude.log

### Git Commands Failing
- Ensure you're in a git repository
- Check git configuration: `git config --list`

### File Not Found
- Use relative paths from current directory
- Use `list directory` to see available files
- Check working directory with `status` command

### Tests/Build Not Auto-detecting
- Ensure standard project files exist (package.json, setup.py, etc.)
- Specify commands explicitly: `run tests with 'pytest'`

## Configuration

Edit `config.json` to customize:
- Model settings (local/cloud)
- Permissions (what operations are allowed)
- Features (enable/disable capabilities)
- Logging levels
- Safety settings

See `config.example.json` for all available options.
