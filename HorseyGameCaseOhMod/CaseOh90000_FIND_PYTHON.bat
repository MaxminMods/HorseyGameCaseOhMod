@echo off
set "CASEOH_PY="

py -3 -c "import sys, tkinter" >nul 2>nul
if not errorlevel 1 set "CASEOH_PY=py -3"

if not defined CASEOH_PY (
  python -c "import sys, tkinter" >nul 2>nul
  if not errorlevel 1 set "CASEOH_PY=python"
)

if not defined CASEOH_PY (
  echo Python 3 with Tkinter was not found.
  echo.
  echo Install Python 3 from:
  echo   https://www.python.org/downloads/
  echo.
  echo During install, enable "Add python.exe to PATH", then run this again.
  exit /b 1
)

exit /b 0
