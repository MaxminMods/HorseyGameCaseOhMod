@echo off
setlocal
cd /d "%~dp0"
call "%~dp0CaseOh90000_FIND_PYTHON.bat"
if errorlevel 1 (
  pause
  exit /b 1
)
echo Starting HorseyGameCaseOhMod v2 easy setup...
echo.
%CASEOH_PY% setup_wizard.py setup --easy
if errorlevel 1 pause
