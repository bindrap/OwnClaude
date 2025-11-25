# OwnClaude Model Selection Guide

## ⚠️ IMPORTANT: Model Size Matters!

OwnClaude works best with **larger, more capable models**. Small models (like llama3.2:3b) often:
- ❌ Don't follow instructions properly
- ❌ Open URLs instead of answering questions
- ❌ Provide incomplete or empty responses
- ❌ Have difficulty with structured JSON output

## 🏆 Recommended Models

### Best Choice (Local)
```bash
# Pull and use Llama 3.1 8B - Best balance of quality and speed
ollama pull llama3.1:8b

# Update config.json:
"model": "llama3.1:8b"
```

**Why this model?**
- ✅ Excellent instruction following
- ✅ Answers questions properly without opening URLs
- ✅ Good at structured output (JSON)
- ✅ Fast enough for interactive use
- ✅ Handles code tasks well

### Alternative Good Models

#### 1. **Llama 3.2 (Latest)**
```bash
ollama pull llama3.2:latest
```
- Good general purpose
- Better than 3b version
- Fast responses

#### 2. **Mistral 7B**
```bash
ollama pull mistral:7b
```
- Excellent code understanding
- Good instruction following
- Fast inference

#### 3. **Qwen2.5 7B**
```bash
ollama pull qwen2.5:7b
```
- Very good at following instructions
- Excellent for code tasks
- Strong reasoning

#### 4. **DeepSeek Coder**
```bash
ollama pull deepseek-coder:6.7b
```
- Specialized for coding tasks
- Good at file operations
- Fast

### Cloud Models (Anthropic)

If you have an Anthropic API key, use Claude:
```json
{
  "model_type": "cloud",
  "ollama": {
    "cloud": {
      "api_key": "your-api-key",
      "endpoint": "https://api.anthropic.com",
      "model": "claude-3-sonnet-20240229"
    }
  }
}
```

## 🚫 Models to Avoid

### llama3.2:3b (Too Small)
**Problems:**
- Opens URLs for factual questions
- Gives empty responses
- Doesn't follow complex instructions
- Poor JSON formatting

**Don't use this unless:** You have very limited RAM (<4GB)

### Other Small Models (<5B parameters)
Generally too small for reliable instruction following.

## 📊 Model Comparison

| Model | Size | Quality | Speed | RAM Needed | Best For |
|-------|------|---------|-------|------------|----------|
| llama3.1:8b | 8B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 8GB | Everything (Best choice) |
| mistral:7b | 7B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 6GB | Code & reasoning |
| qwen2.5:7b | 7B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 6GB | Instructions & code |
| deepseek-coder | 6.7B | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 6GB | Coding tasks only |
| llama3.2:latest | 3B+ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 4GB | Basic tasks |
| llama3.2:3b | 3B | ⭐⭐ | ⭐⭐⭐⭐⭐ | 3GB | Very limited use |

## 🔧 How to Switch Models

### 1. Pull New Model
```bash
ollama pull llama3.1:8b
```

### 2. Update Config
Edit `config.json`:
```json
{
  "model_type": "local",
  "ollama": {
    "local": {
      "host": "http://localhost:11434",
      "model": "llama3.1:8b",  ← Change this
      "temperature": 0.7,
      "top_p": 0.9
    }
  }
}
```

### 3. Restart OwnClaude
```bash
python ownclaude.py
```

## 🎯 Symptoms of Wrong Model

### If You See This:
- ❌ "Opening Wikipedia..." when you ask a question
- ❌ "Providing an answer..." with no actual answer
- ❌ Files created in parent directory (../file.txt)
- ❌ Incomplete or nonsensical responses

### Solution:
**Switch to a larger model immediately!** Try llama3.1:8b or mistral:7b.

## 💡 Pro Tips

### 1. Temperature Settings
```json
"temperature": 0.7  // Good default
"temperature": 0.3  // More focused, less creative (better for code)
"temperature": 0.9  // More creative (better for writing)
```

### 2. Context Length
```json
"features": {
  "max_context_messages": 20  // Increase for longer conversations
}
```

### 3. Check Model Loading
```bash
# See what models you have
ollama list

# See which model is running
ollama ps
```

### 4. Memory Considerations
- **8GB RAM**: Use 7B-8B models
- **16GB RAM**: Can run 13B models
- **32GB+ RAM**: Can run 30B+ models

## 🚀 Quick Fix for Current Issues

Based on your symptoms (URLs opening, empty answers), do this NOW:

```bash
# 1. Pull better model
ollama pull llama3.1:8b

# 2. Edit config.json
# Change: "model": "llama3.2:3b"
# To:     "model": "llama3.1:8b"

# 3. Restart
python ownclaude.py

# 4. Test
You: what is the capital of France?
# Should now answer: "Paris" (not open a URL!)
```

## 📝 Model Performance Examples

### With llama3.2:3b (BAD):
```
You: when did Russia get to the moon?
Bot: Opening Wikipedia...  ❌
```

### With llama3.1:8b (GOOD):
```
You: when did Russia get to the moon?
Bot: The Soviet Union (Russia) sent several unmanned missions to the Moon.
Luna 2 was the first spacecraft to reach the Moon in 1959... ✅
```

## ❓ FAQ

**Q: Will larger models be slower?**
A: Yes, but not dramatically. llama3.1:8b is only ~2x slower than 3b but 10x better quality.

**Q: Can I use cloud models?**
A: Yes! Set `model_type: "cloud"` and configure your API key. Claude or GPT models work excellently.

**Q: How much VRAM do I need?**
A: Models run on CPU by default. VRAM only matters if you have a GPU. 8GB VRAM = 8B models, 24GB = 30B+ models.

**Q: Can I use quantized models?**
A: Yes! Ollama automatically uses quantized versions (Q4). They're already optimized.

**Q: Best model for coding specifically?**
A: DeepSeek-Coder or Qwen2.5:7b for pure coding. Llama3.1:8b for general use including coding.

## 🆘 Still Having Issues?

If switching models doesn't help:

1. **Check Ollama version**: `ollama --version` (update if < 0.1.0)
2. **Restart Ollama**: `ollama serve`
3. **Clear model cache**: `ollama rm <model>` then pull again
4. **Check logs**: `logs/ownclaude.log`
5. **Report issue**: https://github.com/yourusername/OwnClaude/issues

## 🎓 Conclusion

**TL;DR**: Use `llama3.1:8b` or larger. Avoid models smaller than 7B parameters. This will solve most quality issues immediately.

The difference between a 3B and 8B model is night and day for this application!
