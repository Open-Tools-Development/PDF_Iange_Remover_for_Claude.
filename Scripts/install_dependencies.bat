@echo off
setlocal
echo ==================================================
echo    PDF Image Remover  -  Install Dependencies
echo ==================================================
echo.

REM Prefer the Python launcher (py), fall back to python on PATH
set "PYCMD=py -3"
py -3 --version >nul 2>nul
if errorlevel 1 set "PYCMD=python"

%PYCMD% --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on this PC.
    echo.
    echo    1^) Install Python 3.8 or newer from:
    echo       https://www.python.org/downloads/
    echo    2^) During setup, TICK "Add Python to PATH".
    echo    3^) Run this file again.
    echo.
    pause
    exit /b 1
)

echo Using Python:
%PYCMD% --version
echo.
echo Installing required packages (PyMuPDF)...
%PYCMD% -m pip install --upgrade pip
%PYCMD% -m pip install -r "%~dp0requirements.txt"

echo.
if errorlevel 1 (
    echo [ERROR] Installation failed - see the messages above.
) else (
    echo [OK] All set. You can now double-click  run.bat
)
echo.
pause
