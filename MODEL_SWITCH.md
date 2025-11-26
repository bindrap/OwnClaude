# Switching to Code-Specialized Model

## Why Switch to qwen2.5-coder:7b?

Your current setup uses `llama3.1:8b` which is a general-purpose model. For better code generation, editing, and deletion capabilities, `qwen2.5-coder:7b` is specifically trained for coding tasks.

### Expected Improvements:
- **Response Time**: 20-30 seconds (down from 75-90s)
- **Code Quality**: Better at generating, editing, and debugging code
- **Better File Operations**: Improved understanding of file structures and modifications
- **Syntax Accuracy**: More precise code syntax and patterns

## Installation Steps

### 1. Pull the Model
```powershell
ollama pull qwen2.5-coder:7b
```
This will download ~4.7GB. Wait for completion.

### 2. Verify Installation
```powershell
ollama list
```
You should see `qwen2.5-coder:7b` in the list.

### 3. Start OwnClaude
```powershell
.\run.bat
```

## Configuration Already Applied

I've already updated `config.json` to use `qwen2.5-coder:7b`. The change:
- **Line 9**: Changed from `"model": "llama3.1:8b"` to `"model": "qwen2.5-coder:7b"`

## Testing Code Generation

After starting OwnClaude, test with:
```
create a python script that calculates fibonacci sequence
```

Expected: Should generate clean, working code in ~20-30 seconds.

## Alternative Models (If Needed)

### For Maximum Speed (GPU fits entirely):
- **deepseek-coder:1.3b**: 5-15 second responses, fits fully on 4GB GPU
  ```powershell
  ollama pull deepseek-coder:1.3b
  # Edit config.json line 9: "model": "deepseek-coder:1.3b"
  ```

### For Balance:
- **phi3:mini**: 8-15 seconds, good coding ability
  ```powershell
  ollama pull phi3:mini
  # Edit config.json line 9: "model": "phi3:mini"
  ```

### For CPU-Only Mode:
If you want consistent performance without GPU complexity:
```powershell
.\run-cpu.bat
```
Response time: 30-45 seconds (slower but very stable)

## Troubleshooting

### If responses are still slow (60s+):
The model might be using hybrid GPU/CPU mode. Try:
```powershell
ollama stop
.\run.bat
```

### If you get CUDA errors:
Switch to CPU mode:
```powershell
.\run-cpu.bat
```

### To switch back to general-purpose model:
Edit `config.json` line 9 back to:
```json
"model": "llama3.1:8b"
```

## What Makes qwen2.5-coder Better for Code?

1. **Training Data**: Trained specifically on code repositories and programming documentation
2. **Code Understanding**: Better at parsing existing code and making precise edits
3. **Language Support**: Strong support for Python, JavaScript, Java, C++, and 50+ languages
4. **Error Fixing**: Better at identifying and fixing bugs
5. **Documentation**: Generates better code comments and docstrings

## Next Steps After Installation

1. Pull the model with `ollama pull qwen2.5-coder:7b`
2. Run `.\run.bat`
3. Test code generation capabilities
4. If satisfied, commit the config change with git
