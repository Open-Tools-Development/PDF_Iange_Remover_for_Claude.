@echo off
setlocal
echo Starting PDF Image Remover...

REM Prefer the Python launcher (py), fall back to python on PATH
set "PYCMD=py -3"
py -3 --version >nul 2>nul
if errorlevel 1 set "PYCMD=python"

%PYCMD% --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.8+ and run
    echo         install_dependencies.bat first.
    echo.
    pause
    exit /b 1
)

%PYCMD% "%~dp0pdf_image_remover.py"
if errorlevel 1 (
    echo.
    echo The program exited with an error.
    echo If it mentions PyMuPDF is missing, run install_dependencies.bat first.
    echo.
    pause
)
