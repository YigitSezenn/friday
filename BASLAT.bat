@echo off
chcp 65001 >nul
title J.A.R.V.I.S
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Sanal ortam bulunamadi. Once kurulum yapilmali.
    echo python -m venv .venv
    echo .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m jarvis
if errorlevel 1 (
    echo.
    echo JARVIS beklenmedik sekilde kapandi.
    pause
)
