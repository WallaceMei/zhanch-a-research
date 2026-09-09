@echo off
chcp 65001 >nul
"%~dp0.venv\Scripts\python.exe" "%~dp0start_viewer.py"
pause
