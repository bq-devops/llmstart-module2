param(
  [string]$Python = "py -3.11"
)

$ErrorActionPreference = "Stop"

# 1) VENV
if (-not (Test-Path ".venv")) {
  Write-Host "Creating venv..." -ForegroundColor Cyan
  & $Python -m venv .venv
}

# 2) Активируем python из venv для установки пакетов
$venvPy = ".\.venv\Scripts\python.exe"

# 3) Зависимости
Write-Host "Installing requirements..." -ForegroundColor Cyan
& $venvPy -m pip install -r requirements.txt

# 4) .env
if (-not (Test-Path ".env")) {
  if (Test-Path "config/env") {
    Copy-Item "config/env" ".env"
  } else {
    "# Required`nTELEGRAM_BOT_TOKEN=replace_with_your_token" | Out-File -Encoding utf8 ".env"
  }
  Write-Host "Created .env. Please put your TELEGRAM_BOT_TOKEN inside." -ForegroundColor Yellow
}

Write-Host "Setup completed." -ForegroundColor Green
