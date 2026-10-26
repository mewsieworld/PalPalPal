@echo off
REM Builds PalPalPal into one exe. Called by build_32bit.bat (x86) and build_64bit.bat (x64) in the project folder.
REM Usage: build_exe.bat x86   or   build_exe.bat x64
setlocal EnableDelayedExpansion
set ARCH=%~1
if "%ARCH%"=="" set ARCH=x86
cd /d "%~dp0.."
set ROOT=%CD%

if /i "%ARCH%"=="x86" (
    set NAME=PalPalPal
    set BITS=32
) else (
    set NAME=PalPalPal-x64
    set BITS=64
)
echo.
echo === Building %NAME%.exe (%ARCH%, %BITS%-bit) ===
echo.

REM Find a %BITS%-bit Python through the py launcher (newest first)
set PY=
for %%V in (3.13 3.12 3.11 3.10 3) do (
    if not defined PY (
        py -%%V-%BITS% -c "import struct,sys; sys.exit(0 if struct.calcsize('P')*8==%BITS% else 1)" >nul 2>&1
        if !errorlevel! EQU 0 set PY=py -%%V-%BITS%
    )
)
if not defined PY (
    echo ERROR: No %BITS%-bit Python found.
    if "%BITS%"=="32" (
        echo Install the 32-bit Python from https://www.python.org/downloads/windows/
        echo   pick "Windows installer 32-bit" - it installs next to your normal Python.
    ) else (
        echo Install Python from https://www.python.org/downloads/windows/
    )
    echo Then run this script again.
    pause
    exit /b 1
)
echo Using: %PY%
%PY% --version

REM A private build environment, so nothing gets installed into your normal Python
set VENV=%ROOT%\build\venv-%ARCH%
if not exist "%VENV%\Scripts\python.exe" (
    echo Creating the build environment...
    %PY% -m venv "%VENV%" || goto :fail
)
"%VENV%\Scripts\python.exe" -m pip install --quiet --upgrade pip pillow pyinstaller || goto :fail

"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --windowed --name %NAME% --paths "%ROOT%\src" ^
    --add-data "%ROOT%\src\docs;docs" --workpath "%ROOT%\build\%ARCH%" --specpath "%ROOT%\build" ^
    --distpath "%ROOT%\dist" "%ROOT%\src\palpalpal.py"
set RESULT=%errorlevel%
if not %RESULT% EQU 0 goto :fail

echo.
echo === Done: %ROOT%\dist\%NAME%.exe ===
pause
exit /b 0

:fail
echo.
echo ERROR: The build failed. Scroll up for the reason.
pause
exit /b 1
