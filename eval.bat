@echo off
REM ============================================================
REM  BIS Standards Recommender - Evaluation
REM  Runs inference.py the same way judges will.
REM  Defaults to data\sample_test_set.json if no input given.
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo   Running inference.py ^(judge-equivalent command^)
echo ============================================================
echo.

REM Activate venv
if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [ERROR] No venv found. Run setup.bat first.
    pause
    exit /b 1
)

set INPUT=%1
set OUTPUT=%2

if "%INPUT%"=="" set INPUT=data\sample_test_set.json
if "%OUTPUT%"=="" set OUTPUT=data\results.json

echo Input:  %INPUT%
echo Output: %OUTPUT%
echo.

python inference.py --input "%INPUT%" --output "%OUTPUT%"
if errorlevel 1 (
    echo.
    echo [ERROR] Inference failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Done. Results written to %OUTPUT%
echo ============================================================
echo.

REM If the official eval_script.py is present, run it too
if exist "eval_script.py" (
    echo Found eval_script.py - running automated metrics ...
    echo.
    python eval_script.py
    echo.
)

pause
