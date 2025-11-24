# Contributing to OwnClaude

Thank you for your interest in contributing to OwnClaude! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and considerate in all interactions. We want to maintain a welcoming community for everyone.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Detailed steps to reproduce the issue
- Expected vs actual behavior
- Your environment (OS, Python version, Ollama version)
- Any relevant logs or screenshots

### Suggesting Features

Feature suggestions are welcome! Please:
- Check if the feature has already been requested
- Clearly describe the feature and its use case
- Explain why this feature would be useful

### Code Contributions

1. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/OwnClaude.git
   cd OwnClaude
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set Up Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Make Your Changes**
   - Write clear, readable code
   - Follow the existing code style
   - Add docstrings to functions and classes
   - Keep commits focused and atomic

5. **Test Your Changes**
   ```bash
   pytest tests/
   python ownclaude.py --init-config
   python ownclaude.py
   ```

6. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Add feature: brief description"
   ```

7. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

## Development Guidelines

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

### Project Structure

```
OwnClaude/
├── src/ownclaude/
│   ├── core/           # Core functionality
│   │   ├── config.py   # Configuration management
│   │   ├── ollama_client.py  # Ollama API wrapper
│   │   ├── safety.py   # Safety and permissions
│   │   └── executor.py # Command execution
│   ├── modules/        # Feature modules
│   │   ├── app_control.py   # Application control
│   │   └── file_operations.py  # File operations
│   └── utils/          # Utility functions
├── tests/              # Test files
├── docs/               # Documentation
└── ownclaude.py        # Main entry point
```

### Adding New Features

When adding new features:

1. **Create a Module**: If it's a new category of functionality, create a new module in `src/ownclaude/modules/`

2. **Update Executor**: Add the new action type to `CommandExecutor` in `executor.py`

3. **Update System Prompt**: Modify the system prompt to inform the AI about the new capability

4. **Add Safety Checks**: Ensure proper permission checks and safety measures

5. **Document**: Update README and add docstrings

### Safety Considerations

OwnClaude has access to system operations. When contributing:

- Always validate user input
- Implement proper permission checks
- Add confirmation for destructive operations
- Test with sensitive paths blocked
- Consider rollback capabilities

### Testing

- Write tests for new features
- Test on multiple platforms when possible
- Test both success and failure cases
- Verify safety mechanisms work correctly

## Pull Request Process

1. Update the README.md if needed
2. Update documentation for new features
3. Ensure all tests pass
4. Request review from maintainers
5. Address any feedback from reviews

## Areas We Need Help With

- Cross-platform testing (Windows, macOS, Linux)
- Documentation improvements
- New feature implementations
- Bug fixes
- Performance optimizations
- UI/UX enhancements
- Test coverage improvements

## Development Setup Tips

### Local Ollama Setup

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.2

# Start Ollama service
ollama serve
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/ownclaude

# Run specific test file
pytest tests/test_config.py
```

### Code Quality Tools

```bash
# Format code
black src/

# Check style
flake8 src/

# Type checking
mypy src/
```

## Getting Help

- Create an issue for questions
- Join discussions in the GitHub Discussions tab
- Check existing issues and pull requests

## Recognition

Contributors will be recognized in:
- The project README
- Release notes for significant contributions
- The contributors list on GitHub

## License

By contributing to OwnClaude, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to OwnClaude!
