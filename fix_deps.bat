@echo off
REM ============================================================
REM  Fix the recurring groq + httpx version conflict
REM  Run this if you see "Client.__init__() got an unexpected
REM  keyword argument 'proxies'" errors.
REM ============================================================

cd /d "%~dp0"

if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [ERROR] No venv found.
    pause
    exit /b 1
)

echo Pinning compatible groq + httpx versions ...
pip install "groq>=0.13.0" "httpx>=0.27.2,<0.28" --upgrade

echo.
echo Done. Restart the app.
pause
