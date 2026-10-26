@echo off
echo Seat's Taken.

REM Change to the directory where this batch file is located
cd /d "%~dp0"

echo Working directory: %CD%

echo Starting Program...
cd src
python palpalpal.py
set PYTHON_ERROR=%errorlevel%
cd ..

if %PYTHON_ERROR% NEQ 0 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed or not in PATH!
        echo Please install Python from https://python.org
        echo Make sure to check "Add to PATH" during installation.
        pause
        exit /b 1
    ) else (
    echo.
    echo ERROR: The application crashed or failed to start!
    echo This might be due to missing dependencies.
    echo Try running: pip install Pillow
    pause
    exit /b 1
    )
)
