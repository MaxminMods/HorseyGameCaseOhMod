@echo off
setlocal
cd /d "%~dp0"
py -3 setup_wizard.py shortcut
if errorlevel 1 pause
