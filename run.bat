@echo off
REM ============================================================
REM  BIS Standards Recommender - Run Streamlit App
REM  Double-click this file to launch the demo UI
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo   BIS Standards Recommender - Starting Streamlit
echo ============================================================
echo.

REM Activate virtual environment (try common locations)
if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [ERROR] Could not find venv. Expected at:
    echo   - %~dp0..\venv\
    echo   - %~dp0venv\
    echo.
    pause
    exit /b 1
)

REM Check that streamlit is installed
where streamlit >nul 2>&1
if errorlevel 1 (
    echo [ERROR] streamlit not found. Run setup.bat first.
    pause
    exit /b 1
)

echo Launching app at http://localhost:8501 ...
echo Press Ctrl+C in this window to stop.
echo.

streamlit run app.py

pause
