@echo off
setlocal
cd /d "%~dp0"
call "%~dp0CaseOh90000_FIND_PYTHON.bat"
if errorlevel 1 (
  pause
  exit /b 1
)
%CASEOH_PY% setup_wizard.py open-branch
if errorlevel 1 pause
