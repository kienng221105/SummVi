# Automate SummVi Startup

# 0. Ensure .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Setting up .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# 1. Ask user for mode
$choice = Read-Host "How would you like to run SummVi? (1: Local Python/Node, 2: Docker Compose [Recommended])"

if ($choice -eq "2") {
    Write-Host "Starting via Docker Compose..." -ForegroundColor Cyan
    docker-compose up --build
    exit
}

# 2. Kill old processes (Local mode)
Write-Host "Starting in Local mode..." -ForegroundColor Green
Stop-Process -Name python, node, uvicorn, npm -Force -ErrorAction SilentlyContinue 2>$null
Start-Sleep -s 1

# 3. Set Env
$ROOT = Get-Location
$env:PYTHONPATH = $ROOT.Path
$env:LITE_MODE = "true"
$env:NODE_OPTIONS = "--max-old-space-size=4096"

# 4. Start Backend in new window
Write-Host "Starting Backend..."
Start-Process powershell -ArgumentList "-NoExit -Command cd apps/backend; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# 5. Start Frontend in new window
Write-Host "Starting Frontend..."
Start-Process powershell -ArgumentList "-NoExit -Command cd apps/frontend; npm run dev"

Write-Host "Done! Check the new windows for logs."
