@echo off
setlocal
cd /d "%~dp0HorseyGameCaseOhMod"
if errorlevel 1 (
  echo Could not open the HorseyGameCaseOhMod folder.
  pause
  exit /b 1
)
call "CaseOh90000_FIND_PYTHON.bat"
if errorlevel 1 (
  pause
  exit /b 1
)
%CASEOH_PY% setup_wizard.py setup --run
if errorlevel 1 pause
