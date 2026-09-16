@echo off
title Gemini Flash Chatbot Service (Cloud Run Local Test)

echo ========================================================
echo   Gemini Flash Chatbot Service (Cloud Run Local Test)
echo   Port: 8080 (Cloud Run Default)
echo   Models: Gemini 3.8 Flash / Gemini 3.7 Flash
echo ========================================================
echo.

cd /d "%~dp0"
set PORT=8080

REM 1. Check Miniconda Python directly
if exist "C:\Users\%USERNAME%\miniconda3\python.exe" (
    echo [Python Path] C:\Users\%USERNAME%\miniconda3\python.exe
    "C:\Users\%USERNAME%\miniconda3\python.exe" app.py
    goto :DONE
)

REM 2. Check Python Launcher
where py >nul 2>nul
if %errorlevel% equ 0 (
    echo [Python Path] py -3
    py -3 app.py
    goto :DONE
)

REM 3. Fallback to python command
echo [Python Path] python
python app.py

:DONE
pause
