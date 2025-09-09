$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "venv not found. Run ./setup.ps1 first." -ForegroundColor Yellow
  exit 1
}

Write-Host "Starting bot..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m bot.main
