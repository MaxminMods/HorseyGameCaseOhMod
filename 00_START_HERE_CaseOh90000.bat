@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 was not found. Please install Python 3, then run this again.
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)
py -3 setup_wizard.py setup --run
if errorlevel 1 pause
