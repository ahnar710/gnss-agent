@echo off
rem GNSS Literature Research Agent - one-click Windows build
rem Builds PyInstaller bundle, then Inno Setup installer if available.
cd /d "%~dp0.."

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

echo Building GNSS Literature Research Agent...
%PY% packaging\build.py

echo.
pause
