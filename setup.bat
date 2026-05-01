@echo off
REM ============================================================
REM  BIS Standards Recommender - First-time setup
REM  Installs dependencies and builds the search index.
REM  Run this ONCE after cloning, or whenever requirements change.
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo   BIS Standards Recommender - Setup
echo ============================================================
echo.

REM Activate virtual environment
if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [ERROR] No venv found. Create one first:
    echo   python -m venv venv
    echo.
    pause
    exit /b 1
)

echo [1/3] Upgrading pip ...
python -m pip install --upgrade pip --quiet

echo.
echo [2/3] Installing dependencies (this takes 3-5 min the first time) ...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] pip install failed. See messages above.
    pause
    exit /b 1
)

echo.
echo [3/3] Checking for .env file ...
if not exist ".env" (
    echo.
    echo [WARNING] .env file not found. Copying from .env.example ...
    copy ".env.example" ".env" >nul
    echo.
    echo  ! IMPORTANT ! Open .env and add your GROQ_API_KEY before running.
    echo   Get a free key at: https://console.groq.com/keys
    echo.
)

echo.
echo ============================================================
echo   Setup complete!
echo ============================================================
echo.
echo Next steps:
echo   1. If .env was just created, edit it and add your GROQ_API_KEY
echo   2. Drop SP 21 PDFs into data\raw_pdfs\
echo   3. Run build_index.bat to build the search index
echo   4. Run run.bat to launch the app
echo.
pause
