@echo off
REM PBOS AI CPU-Only Launcher
REM For when GPU causes issues or you need maximum stability

echo ========================================
echo   PBOS AI (Personal Bot OS) CPU Mode
echo ========================================
echo.
echo Configuring Ollama for CPU-only mode...

REM Stop existing Ollama instance
echo Stopping existing Ollama server...
taskkill /F /IM ollama.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM Set environment variables for CPU-only mode
set OLLAMA_NUM_CTX=2048
set OLLAMA_NUM_GPU=0
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_NUM_THREAD=8

echo ✓ Context: 2048 tokens
echo ✓ GPU Layers: 0 (CPU only)
echo ✓ Threads: 8 (optimized for multi-core CPU)
echo.
echo Starting Ollama server in CPU mode...

REM Start Ollama server in background
start /B ollama serve

REM Wait for Ollama to be ready
timeout /t 3 /nobreak >nul

echo ✓ Ollama server started
echo.
echo This configuration:
echo   - 100%% CPU mode (no GPU)
echo   - Slower but VERY stable
echo   - Expected response time: 3-8 seconds
echo.
echo Starting PBOS AI...
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
