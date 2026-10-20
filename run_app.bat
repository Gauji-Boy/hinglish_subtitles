@echo off
cd /d "%~dp0"
set HF_HOME=D:\Hinglish_subtitles\models\huggingface

:: Check if user configured console mode in the UI
if exist launch_config.json (
    findstr /c:"\"silent_launch\": false" launch_config.json >nul 2>&1
    if not errorlevel 1 goto console_mode
)

:silent_mode
wscript.exe //B "%~dp0run_app_no_terminal.vbs"
exit /b

:console_mode
title Hinglish Subtitle Generator (Console Mode)
python server.py
pause
exit /b
