@echo off
setlocal
cd /d "%~dp0"
py -3 setup_wizard.py caseoh-off
if errorlevel 1 pause
