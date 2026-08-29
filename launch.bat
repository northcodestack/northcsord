@echo off
title NorthCord Launcher
echo ============================================================
echo   🚀 NorthCord Launcher
echo   Discord, reimagined for the terminal.
echo ============================================================

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

:: Run python launcher script
python launcher.py
