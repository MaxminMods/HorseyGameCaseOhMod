@echo off
setlocal

set "APPDIR=%~dp0HorseyGameCaseOhMod"
set "CONFIG=%APPDIR%\CaseOh90000_paths.json"
set "LOG=%APPDIR%\CaseOh90000_play.log"

if /i "%~1"=="--hidden-run" goto run_play

if not exist "%CONFIG%" (
  call "%~dp000_START_HERE_CaseOh90000.bat"
  exit /b %errorlevel%
)

set "CASEOH_PLAY_BAT=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$bat=$env:CASEOH_PLAY_BAT; Start-Process -WindowStyle Hidden -FilePath $bat -ArgumentList '--hidden-run'"
exit /b 0

:run_play
cd /d "%APPDIR%" >nul 2>nul
if errorlevel 1 exit /b 1
call "CaseOh90000_FIND_PYTHON.bat" >> "%LOG%" 2>&1
if errorlevel 1 exit /b 1
%CASEOH_PY% setup_wizard.py run --panel >> "%LOG%" 2>&1
exit /b %errorlevel%
