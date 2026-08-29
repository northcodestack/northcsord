#!/usr/bin/env pwsh
# NorthCord Launcher - PowerShell

Write-Host "="*60 -ForegroundColor Cyan
Write-Host "  🚀 NorthCord Launcher" -ForegroundColor Yellow
Write-Host "  Discord, reimagined for the terminal." -ForegroundColor Gray
Write-Host "="*60 -ForegroundColor Cyan

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found! Please install Python 3.10+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Run python launcher script
python launcher.py
