@echo off
REM One click: builds the 32-bit (x86) PalPalPal.exe into the dist folder. Needs a 32-bit Python installed.
call "%~dp0build_tools\build_exe.bat" x86
