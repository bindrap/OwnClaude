# OwnClaude

A terminal-based AI assistant that performs computer tasks on your behalf - from opening applications and managing files to helping with coding and answering questions. Your personal AI companion for productivity and automation.

## Overview

OwnClaude is a command-line AI assistant designed to help you control your computer through natural language commands. Whether you need to open your email, close browsers, edit Excel files, write code, or get quick answers, OwnClaude handles it all from your terminal.

## Features

- **Application Control**: Open and close applications (mail clients, browsers, Excel, etc.)
- **File Management**: Create, edit, and organize files
- **Coding Assistant**: Write, edit, and debug code
- **Task Automation**: Automate repetitive computer tasks
- **Question Answering**: Get quick answers to your questions
- **Natural Language Interface**: Communicate with your computer naturally

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

## Usage

### Starting OwnClaude

```bash
python ownclaude.py
```

### Example Commands

```
> open my email
Opening default email client...

> close all browser windows
Closing all browser instances...

> create a Python script that prints hello world
Creating hello.py...

> open the sales report Excel file
Opening sales_report.xlsx...

> help me debug this code: [paste code]
Analyzing your code...

> what's the weather today?
Let me check that for you...
```

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