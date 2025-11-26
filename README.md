# OwnClaude

A terminal-based AI assistant that performs computer tasks on your behalf - from opening applications and managing files to helping with coding and answering questions. Your personal AI companion for productivity and automation.

## Overview

OwnClaude is a command-line AI assistant designed to help you control your computer through natural language commands. Whether you need to open your email, close browsers, edit Excel files, write code, or get quick answers, OwnClaude handles it all from your terminal.

## Features

### 🚀 Core Capabilities
- **Application Control**: Open and close applications (mail clients, browsers, Excel, etc.)
- **File Management**: Create, read, modify, append, and delete files and directories
- **Natural Language Interface**: Communicate with your computer naturally
- **Conversation Memory**: Maintains context throughout your session

### 💻 Code Development
- **Code Navigation**: Search code with grep, find definitions of functions/classes
- **Syntax Analysis**: Analyze Python files for structure, imports, and dependencies
- **Code Search**: Find functions, classes, variables across your codebase
- **Project Understanding**: Auto-detect project type and structure

### 🔧 Development Tools
- **Terminal Commands**: Execute shell commands with safety checks
- **Test Execution**: Auto-detect and run tests (pytest, npm test, cargo test, etc.)
- **Build Automation**: Auto-detect and run builds for your project type
- **Linter Integration**: Run code quality checks automatically

### 🌳 Git Integration
- **Repository Status**: Check current branch, staged/unstaged files
- **Diff Viewing**: See what changes you've made
- **Commit Creation**: Stage and commit changes
- **Branch Management**: Create, switch, and list branches
- **Commit History**: View file and project history

### 🎯 Advanced Features
- **Task Planning**: Creates execution plans before running complex tasks
- **Multi-step Execution**: Handles complex workflows automatically
- **Context Awareness**: Understands your project structure and files
- **Safety Checks**: Prevents dangerous commands, requires confirmation for destructive operations
- **Rollback Support**: Undo file operations when needed
- **Operation Logging**: Track all actions for review

## Model Options

OwnClaude supports two deployment modes:

### 1. Local Model (Ollama)
Run AI models directly on your machine for privacy and offline access.

**Advantages:**
- Complete privacy - data never leaves your machine
- No internet required
- No API costs
- Low latency for local operations

**Requirements:**
- [Ollama](https://ollama.ai/) installed locally
- Sufficient RAM (8GB+ recommended)
- Compatible models: Llama 3.2, Mistral, CodeLlama, etc.

### 2. Cloud API (Ollama Cloud)
Use cloud-hosted models for more powerful capabilities.

**Advantages:**
- Access to larger, more capable models
- No local resource requirements
- Consistent performance across devices

**Requirements:**
- Internet connection
- API credentials

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/OwnClaude.git
cd OwnClaude

# Install dependencies
pip install -r requirements.txt

# Configure your model preference
cp config.example.json config.json
# Edit config.json with your preferred settings
```

## Configuration

Edit `config.json` to set your preferences:

```json
{
  "model_type": "local",  // "local" or "cloud"
  "ollama": {
    "local": {
      "host": "http://localhost:11434",
      "model": "llama3.2"
    },
    "cloud": {
      "api_key": "your-api-key-here",
      "endpoint": "https://cloud.ollama.ai"
    }
  },
  "system_permissions": {
    "allow_app_control": true,
    "allow_file_operations": true,
    "allow_browser_control": true
  }
}
```

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/OwnClaude.git
cd OwnClaude

# Install dependencies
pip install -r requirements.txt

# Create configuration
python ownclaude.py --init-config
# Edit config.json with your settings
```

### 2. Start Ollama

```bash
# For local models
ollama serve

# Pull a model if you haven't already
ollama pull llama3.2
```

### 3. Run OwnClaude

```bash
python ownclaude.py
```

## Usage Examples

### Basic Commands

```bash
# File operations
You: create a Python script called hello.py that prints hello world
You: show me what's in hello.py
You: add a goodbye function to hello.py

# Application control
You: open my browser
You: launch calculator
You: close all chrome windows

# Questions
You: what is the difference between list and tuple in Python?
```

### Code Development

```bash
# Search code
You: search for "def process" in Python files
You: find the definition of UserAuth class
You: show me all TODO comments

# Project analysis
You: give me a summary of this project
You: what's the project structure?
You: analyze the main.py file
```

### Terminal & Testing

```bash
# Run commands
You: run 'ls -la' to show files
You: install the requests package

# Testing and building
You: run the tests
You: build the project
You: check code style with linter
```

### Git Operations

```bash
# Check status and changes
You: what's the git status?
You: show me the diff
You: show the last 5 commits

# Make changes
You: stage all Python files
You: commit with message "Add new feature"
You: create a branch called feature-auth
```

### Advanced Workflows

```bash
# Complex multi-step tasks
You: I want to create a new feature branch, add a login function, run tests, and commit the changes

# Code review
You: review the code I just created
You: diagnose why my tests are failing

# Project setup
You: help me set up a new Python project with proper structure
```

See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) for comprehensive examples and workflows.

## Supported Tasks

### Application Management
- Open applications (browsers, email, office apps)
- Close running applications
- Switch between applications

### File Operations
- Create, edit, and delete files
- Search for files
- Organize directories

### Coding Assistance
- Write code in multiple languages
- Debug existing code
- Explain code functionality
- Refactor and optimize code

### System Tasks
- Execute terminal commands
- Automate workflows
- Schedule tasks

## Safety Features

OwnClaude includes several safety mechanisms:

- **Permission System**: Configurable permissions for different operation types
- **Confirmation Prompts**: Critical operations require user confirmation
- **Operation Logging**: All actions are logged for review
- **Rollback Capability**: Undo accidental changes when possible

## Development Roadmap

- [ ] Voice input support
- [ ] Multi-language support
- [ ] Plugin system for extensions
- [ ] GUI overlay option
- [ ] Integration with popular productivity tools
- [ ] Custom automation scripts
- [ ] Learning from user preferences

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Privacy & Security

- All local model processing happens on your machine
- No telemetry or data collection
- Open source and auditable
- Configurable permission system

## Requirements

- Python 3.8+
- Windows/Linux/macOS
- Ollama (for local models)
- 4GB+ RAM minimum (8GB+ recommended for local models)

## License

MIT License - see [LICENSE](LICENSE) for details

## Troubleshooting

### Ollama Not Connecting
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve
```

### Permission Errors
Ensure OwnClaude has necessary system permissions in your OS settings.

### Model Not Found
```bash
# Pull the required model
ollama pull llama3.2
```

## Support

- Issues: [GitHub Issues](https://github.com/yourusername/OwnClaude/issues)
- Documentation: [Wiki](https://github.com/yourusername/OwnClaude/wiki)
- Community: [Discussions](https://github.com/yourusername/OwnClaude/discussions)

## Acknowledgments

Built with:
- [Ollama](https://ollama.ai/) - Local LLM runtime
- Python - Core programming language
- Various open-source libraries

---

**Note**: OwnClaude is designed to be a helpful assistant. Always review critical operations before execution and maintain regular backups of important data.