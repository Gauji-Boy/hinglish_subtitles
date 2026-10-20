@echo off
title Stop Hinglish Subtitle Generator
echo Stopping Hinglish Subtitle Generator background processes...
for /l %%p in (8501,1,8530) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%%p " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
)
echo Done! All background generator servers have been stopped.
timeout /t 2 >nul
