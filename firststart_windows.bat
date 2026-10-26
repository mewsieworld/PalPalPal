@echo off
REM Change to the directory where this batch file is located
cd /d "%~dp0"
echo Working directory: %CD%

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python from https://python.org and make sure to check "Add to PATH" during installation.
    echo After installing Python, restart your computer and try again.
    pause
    exit /b 1
)

REM Check if pip exists and install if needed ===
echo Checking pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Pip not found. Trying to install pip...
    python -m ensurepip --default-pip >nul 2>&1
    if errorlevel 1 (
        echo WARNING: 'ensurepip' failed or pip is externally managed.
        echo Attempting fallback check for pip...
    )

    REM Recheck if pip was installed successfully after ensurepip attempt
    python -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Pip is still not working!
        echo Please try the following:
        echo 1. Right-click this script and choose "Run as administrator"
        echo 2. Or manually install pip from https://pip.pypa.io
        pause
        exit /b 1
    ) else (
        echo Pip installed successfully.
        python -m pip install --upgrade pip --no-warn-script-location >nul 2>&1
    )
) else (
    echo Pip is working.
)

REM Check if Pillow is installed
echo Checking for required dependencies...
python -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo Installing Pillow...
    python -m pip install Pillow --no-warn-script-location >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to install Pillow! Please try:
        echo 1. Right-click this script
        echo 2. Select "Run as administrator"
        echo 3. After Pillow installs, you can run normally by double-clicking
        pause
        exit /b 1
    )
    echo Pillow installed successfully.
) else (
    echo Pillow is installed.
)

REM Check if src folder exists
if not exist "src" (
    echo ERROR: src folder not found!
    echo Make sure this batch file is in the same folder as the src folder
    pause
    exit /b 1
)

REM Check if required Python files exist
if not exist "src\palpalpal.py" (
    echo Error: src\launch_previewer.py not found!
    echo Please redownload the repository and try again.
    pause
    exit /b 1
)

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
