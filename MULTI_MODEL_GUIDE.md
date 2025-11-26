# Multi-Model Routing Guide

## Overview

OwnClaude now supports intelligent model routing! The system automatically selects the best model based on your question type.

## How It Works

When you ask a question, the system analyzes your input for trigger words and routes to the appropriate model:

- **Code Questions** → `qwen2.5-coder:7b` (specialized for programming)
- **General Questions** → `qwen2.5:7b` (excellent general knowledge)
- **Math Questions** → `qwen2.5:7b` (good at calculations)
- **Default** → `qwen2.5:7b` (fallback for everything else)

## Configuration

The routing is controlled in `config.json`:

```json
{
  "enable_model_routing": true,
  "model_routing": {
    "default_model": "qwen2.5:7b",
    "models": {
      "code": {
        "model": "qwen2.5-coder:7b",
        "triggers": ["write code", "create script", "debug", "fix error",
                     "implement", "function", "class", "program",
                     "edit file", "modify code", "refactor"]
      },
      "general": {
        "model": "qwen2.5:7b",
        "triggers": ["what is", "how does", "explain", "tell me about",
                     "why", "when", "who", "where", "define"]
      },
      "math": {
        "model": "qwen2.5:7b",
        "triggers": ["calculate", "solve", "equation", "math", "formula"]
      }
    }
  }
}
```

## Examples

### Code Routing
**Input:** "write code to sort an array"
**Routed to:** qwen2.5-coder:7b (matches "write code" trigger)

**Input:** "create script that backs up files"
**Routed to:** qwen2.5-coder:7b (matches "create script" trigger)

**Input:** "debug this function"
**Routed to:** qwen2.5-coder:7b (matches "debug" trigger)

### General Knowledge Routing
**Input:** "what is photosynthesis?"
**Routed to:** qwen2.5:7b (matches "what is" trigger)

**Input:** "explain how engines work"
**Routed to:** qwen2.5:7b (matches "explain" trigger)

**Input:** "tell me about the French Revolution"
**Routed to:** qwen2.5:7b (matches "tell me about" trigger)

### Default Routing
**Input:** "how are you today?"
**Routed to:** qwen2.5:7b (no trigger match, uses default)

## Required Models

Install both models for full functionality:

```powershell
# General knowledge + math model
ollama pull qwen2.5:7b

# Code specialist model
ollama pull qwen2.5-coder:7b
```

**Total Size:** ~9.4GB (4.7GB each)

## GPU Usage

With 3.5GB GPU allocation:
- Both models share the same GPU layers (18 of 32)
- Model switching is fast (~1-2 seconds)
- No additional VRAM needed

## Customizing Triggers

You can add your own triggers in `config.json`:

```json
"models": {
  "code": {
    "model": "qwen2.5-coder:7b",
    "triggers": ["write code", "debug", "YOUR CUSTOM TRIGGER HERE"]
  }
}
```

**Trigger Matching:**
- Case-insensitive
- Matches anywhere in your input
- First match wins

## Adding New Model Types

You can add specialized models for specific tasks:

```json
"models": {
  "code": { ... },
  "general": { ... },
  "creative": {
    "model": "mistral:7b",
    "triggers": ["write story", "poem", "creative", "imagine"],
    "description": "Creative writing and storytelling"
  }
}
```

Then install the model:
```powershell
ollama pull mistral:7b
```

## Disabling Routing

To use a single model for everything:

**Option 1:** Disable in config.json:
```json
"enable_model_routing": false
```

**Option 2:** Set all models to the same:
```json
"default_model": "qwen2.5:7b",
"models": {
  "code": { "model": "qwen2.5:7b", ... },
  "general": { "model": "qwen2.5:7b", ... }
}
```

## Performance

### With Routing (18 GPU layers):
- **Code questions:** 20-30 seconds (qwen2.5-coder:7b)
- **General questions:** 20-30 seconds (qwen2.5:7b)
- **Model switching:** 1-2 seconds

### Without Routing (single model):
- **All questions:** 20-30 seconds
- **No switching delay**

## Troubleshooting

### Model not found error
```
Error: model 'qwen2.5-coder:7b' not found
```
**Fix:** Install the missing model:
```powershell
ollama pull qwen2.5-coder:7b
```

### Wrong model being used
Check the console output. It shows which model is being used:
```
[dim]Using local model: qwen2.5-coder:7b[/dim]
```

Enable debug logging to see routing decisions:
```json
"logging": {
  "level": "DEBUG"
}
```

### Routing not working
1. Verify `enable_model_routing: true` in config.json
2. Check trigger words match your input
3. Restart OwnClaude after config changes

## Best Practices

1. **Use descriptive triggers:** More specific triggers = better routing
2. **Don't overlap triggers:** Avoid same trigger in multiple models
3. **Test your triggers:** Try sample questions to verify routing
4. **Monitor performance:** Check if routing improves response quality
5. **Keep models updated:** Run `ollama pull <model>` periodically

## FAQ

**Q: Can I use more than 2 models?**
A: Yes! Add as many as you want. Each just needs a name, model, and triggers.

**Q: Does routing slow down responses?**
A: No. Routing adds <0.1 seconds (just checking trigger words).

**Q: Can I use different model sizes?**
A: Yes, but be careful with GPU memory. A 13B model needs ~6-7GB.

**Q: What if no trigger matches?**
A: It uses the `default_model` (qwen2.5:7b).

**Q: Can I manually specify a model?**
A: Not yet, but you can adjust triggers or disable routing for specific use.

## GPU Memory Guide

For 4GB GPU with 18 layers (~3.5GB):
- ✅ Two 7B models (they share GPU, not additive)
- ✅ One 8B model
- ❌ One 13B model (needs 6-7GB)
- ❌ One 70B model (needs 40GB+)

## Next Steps

1. Install required models:
   ```powershell
   ollama pull qwen2.5:7b
   ollama pull qwen2.5-coder:7b
   ```

2. Verify config has routing enabled:
   ```json
   "enable_model_routing": true
   ```

3. Start OwnClaude:
   ```powershell
   .\run.bat
   ```

4. Test it:
   - Ask a code question: "write code to calculate fibonacci"
   - Ask a general question: "what is quantum mechanics?"
   - Watch which model responds!

Enjoy your intelligent multi-model assistant! 🚀
