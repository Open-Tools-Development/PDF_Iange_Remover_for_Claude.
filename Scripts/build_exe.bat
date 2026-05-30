@echo off
setlocal
echo ==================================================
echo    PDF Image Remover  -  Build Windows EXE
echo ==================================================
echo.

REM Prefer the Python launcher (py), fall back to python on PATH
set "PYCMD=py -3"
py -3 --version >nul 2>nul
if errorlevel 1 set "PYCMD=python"

%PYCMD% --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.8+ first.
    echo.
    pause
    exit /b 1
)

echo Installing build tools (PyMuPDF + PyInstaller)...
%PYCMD% -m pip install --upgrade pip
%PYCMD% -m pip install -r "%~dp0requirements.txt" pyinstaller
echo.

echo Building single-file executable (this can take a minute)...
%PYCMD% -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "PDFImageRemover" ^
    --collect-all pymupdf ^
    "%~dp0pdf_image_remover.py"

echo.
if exist "%~dp0dist\PDFImageRemover.exe" (
    echo [OK] Build complete.
    echo Your program is here:
    echo     %~dp0dist\PDFImageRemover.exe
    echo You can copy that .exe anywhere and run it without Python.
) else (
    echo [ERROR] Build did not produce an exe - see the messages above.
)
echo.
pause
