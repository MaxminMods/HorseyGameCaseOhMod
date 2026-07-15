@echo off
setlocal
cd /d "%~dp0"
call "%~dp0CaseOh90000_FIND_PYTHON.bat"
if errorlevel 1 (
  pause
  exit /b 1
)
echo Starting HorseyGameCaseOhMod 3.0 easy setup...
echo.
if exist "%~dp0CaseOh90000_paths.json" (
  %CASEOH_PY% setup_wizard.py run --panel
) else (
  %CASEOH_PY% setup_wizard.py setup --easy
)
if errorlevel 1 pause
