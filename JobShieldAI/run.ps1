# JobShield AI — one-command local startup for Windows PowerShell.
#
#   .\run.ps1              build the React UI if needed, then serve on :8000
#   .\run.ps1 -NoBuild     skip the frontend build step
#   .\run.ps1 -Reload      enable uvicorn auto-reload for backend development
#
# Serves the FastAPI backend and the compiled React app from one port, so the UI and
# API share an origin and no proxy is needed.

param(
    [switch]$NoBuild,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$Port = if ($env:JOBSHIELD_PORT) { $env:JOBSHIELD_PORT } else { "8000" }
$HostAddr = if ($env:JOBSHIELD_HOST) { $env:JOBSHIELD_HOST } else { "0.0.0.0" }

Write-Host "[1/4] Checking Python dependencies..." -ForegroundColor Cyan
python -c "import fastapi, sklearn, pandas, bs4" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Installing from requirements.txt (this runs once)..." -ForegroundColor Yellow
    python -m pip install -q -r requirements.txt
}

Write-Host "[2/4] Checking trained model artifacts..." -ForegroundColor Cyan
if (-not (Test-Path "saved_models\model.pkl") -or -not (Test-Path "saved_models\tfidf_vectorizer.pkl")) {
    Write-Host "      Artifacts missing - generating dataset and training..." -ForegroundColor Yellow
    python data\create_dataset.py
    python model\train_model.py
}

if (-not $NoBuild) {
    Write-Host "[3/4] Building the React UI..." -ForegroundColor Cyan
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Push-Location frontend
        if (-not (Test-Path "node_modules")) { npm install --silent }
        npm run build --silent
        Pop-Location
    } else {
        Write-Host "      npm not found - skipping. Install Node.js for the UI." -ForegroundColor Yellow
    }
} else {
    Write-Host "[3/4] Skipping frontend build (-NoBuild)." -ForegroundColor Cyan
}

Write-Host "[4/4] Starting JobShield AI on http://localhost:$Port" -ForegroundColor Green
Write-Host "      API docs: http://localhost:$Port/docs" -ForegroundColor Green
$env:JOBSHIELD_PORT = $Port
$env:JOBSHIELD_HOST = $HostAddr
$env:JOBSHIELD_RELOAD = if ($Reload) { "1" } else { "0" }
python api.py
