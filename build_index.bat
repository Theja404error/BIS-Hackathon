@echo off
REM ============================================================
REM  BIS Standards Recommender - Build Search Index
REM  Run this ONCE after dropping PDFs into data\raw_pdfs\
REM  Or whenever you want to re-ingest the dataset.
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo   Building search index from PDFs in data\raw_pdfs\
echo ============================================================
echo.

REM Activate virtual environment
if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo [ERROR] No venv found. Run setup.bat first.
    pause
    exit /b 1
)

REM Verify PDFs exist
dir /b "data\raw_pdfs\*.pdf" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No PDFs found in data\raw_pdfs\
    echo Drop the BIS SP 21 PDFs into that folder, then run this script again.
    pause
    exit /b 1
)

echo [1/2] Parsing PDFs into chunks ...
python -m src.ingest
if errorlevel 1 (
    echo [ERROR] Ingestion failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Building BM25 + dense embedding indices ...
python -m src.retriever
if errorlevel 1 (
    echo [ERROR] Index build failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Index built successfully!
echo ============================================================
echo.
echo Now run.bat to launch the app, or eval.bat to test inference.
echo.
pause
