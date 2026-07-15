@echo off
setlocal

set "APPDIR=%~dp0HorseyGameCaseOhMod"
set "CONFIG=%APPDIR%\CaseOh90000_paths.json"
set "STEAM_HORSEY=%ProgramFiles(x86)%\Steam\steamapps\common\Horsey Game\Horsey.exe"
set "LOG=%APPDIR%\CaseOh90000_start_here.log"

if /i "%~1"=="--hidden-setup" goto run_setup
if /i "%~1"=="--hidden-play" goto run_play

if exist "%CONFIG%" goto play_hidden
if exist "%STEAM_HORSEY%" goto setup_hidden
goto run_visible

:setup_hidden
set "CASEOH_START_BAT=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$bat=$env:CASEOH_START_BAT; Start-Process -WindowStyle Hidden -FilePath $bat -ArgumentList '--hidden-setup'"
exit /b 0

:play_hidden
set "CASEOH_START_BAT=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$bat=$env:CASEOH_START_BAT; Start-Process -WindowStyle Hidden -FilePath $bat -ArgumentList '--hidden-play'"
exit /b 0

:run_visible
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
echo Starting HorseyGameCaseOhMod 3.0 easy setup...
echo.
%CASEOH_PY% setup_wizard.py setup --easy
if errorlevel 1 pause
exit /b %errorlevel%

:run_setup
cd /d "%APPDIR%" >nul 2>nul
if errorlevel 1 exit /b 1
call "CaseOh90000_FIND_PYTHON.bat" >> "%LOG%" 2>&1
if errorlevel 1 exit /b 1
%CASEOH_PY% setup_wizard.py setup --easy >> "%LOG%" 2>&1
exit /b %errorlevel%

:run_play
cd /d "%APPDIR%" >nul 2>nul
if errorlevel 1 exit /b 1
call "CaseOh90000_FIND_PYTHON.bat" >> "%LOG%" 2>&1
if errorlevel 1 exit /b 1
%CASEOH_PY% setup_wizard.py run --panel >> "%LOG%" 2>&1
exit /b %errorlevel%
