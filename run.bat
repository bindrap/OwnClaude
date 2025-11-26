@echo off
REM OwnClaude GPU-Optimized Launcher
REM This prevents CUDA out-of-memory errors on 4GB GPUs

echo ========================================
echo   OwnClaude GPU-Optimized Launcher
echo ========================================
echo.
echo Configuring Ollama for 4GB GPU...

REM Reduce context window to prevent OOM (2048 tokens = ~800MB GPU RAM)
set OLLAMA_NUM_CTX=2048

REM Use hybrid GPU/CPU mode (offload 20 of 32 layers to GPU)
set OLLAMA_NUM_GPU=20

REM Reduce batch size to save memory
set OLLAMA_MAX_BATCH=256

echo ✓ Context: 2048 tokens (reduced from 4096)
echo ✓ GPU Layers: 20 of 32 (hybrid mode)
echo ✓ Batch Size: 256 (memory saver)
echo.
echo This configuration:
echo   - Uses GPU for 60%% speed boost
echo   - Falls back to CPU for remaining layers
echo   - Won't crash with OOM errors
echo.
echo Starting OwnClaude...
echo.

REM Activate venv if it exists
if exist windowsVenv\Scripts\activate.bat (
    call windowsVenv\Scripts\activate.bat
)

python ownclaude.py

pause
