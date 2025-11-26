@echo off
REM OwnClaude GPU-Optimized Launcher
REM This prevents CUDA out-of-memory errors on 4GB GPUs

echo ========================================
echo   OwnClaude GPU-Optimized Launcher
echo ========================================
echo.
echo Configuring Ollama for 4GB GPU...

REM Stop existing Ollama instance
echo Stopping existing Ollama server...
taskkill /F /IM ollama.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM Set environment variables for Ollama (OPTIMIZED for 3.5GB GPU usage)
set OLLAMA_NUM_CTX=2048
set OLLAMA_NUM_GPU=18
set OLLAMA_NUM_PARALLEL=1

echo ✓ Context: 2048 tokens (reduced from 4096)
echo ✓ GPU Layers: 18 of 32 (~3.5GB GPU usage)
echo ✓ Memory optimized for maximum 4GB GPU performance
echo.
echo Starting Ollama server with optimized settings...

REM Start Ollama server in background with settings
start /B ollama serve

REM Wait for Ollama to be ready
timeout /t 3 /nobreak >nul

echo ✓ Ollama server started
echo.
echo This configuration:
echo   - Uses GPU for 18 layers (~3.5GB VRAM)
echo   - Falls back to CPU for remaining 14 layers
echo   - OPTIMIZED: Maximum performance on 4GB GPU
echo.
echo Starting OwnClaude...
echo.

REM Activate venv if it exists
if exist windowsVenv\Scripts\activate.bat (
    call windowsVenv\Scripts\activate.bat
)

python ownclaude.py

REM Cleanup: Stop Ollama when done
echo.
echo Stopping Ollama server...
taskkill /F /IM ollama.exe >nul 2>&1

pause
