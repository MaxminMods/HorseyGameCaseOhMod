@echo off
setlocal
cd /d "%~dp0"
py -3 setup_wizard.py panel
if errorlevel 1 pause
