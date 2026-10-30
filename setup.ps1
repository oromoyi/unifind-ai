# UniFind AI - one-time setup for Windows PowerShell (run from the repository root)
# Usage:  powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
Write-Host "== Backend ==" -ForegroundColor Cyan
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created backend\.env - EDIT the DB_PASSWORD and SECRET_KEY values before continuing." -ForegroundColor Yellow }
Set-Location ..
Write-Host "== Frontend ==" -ForegroundColor Cyan
Set-Location frontend
npm install
Set-Location ..
Write-Host "Done. Next: create the MySQL database (see README step 3), then run backend\.venv\Scripts\python.exe backend\seed.py" -ForegroundColor Green
