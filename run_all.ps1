# SummVi - Single-Command Startup
# Usage:  .\run_all.ps1          (from project root)

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

$modelEndpoint = "https://kiencnt2205-summ-vi-v2.hf.space"
$choice = Read-Host "Run SummVi? (1: Local, 2: Docker)"

$env:MODEL_SERVICE_URL = $modelEndpoint

if ($choice -eq "2") {
    Write-Host ""
    Write-Host "  === SummVi - Starting Core Services ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Services:" -ForegroundColor Yellow
    Write-Host "    PostgreSQL      localhost:5432"
    Write-Host "    Model Endpoint  $modelEndpoint"
    Write-Host "    Backend API     http://localhost:8000"
    Write-Host "    Frontend        http://localhost:3000"
    Write-Host "    Swagger Docs    http://localhost:8000/docs"
    Write-Host ""
    docker compose up --build -d
    exit
}

# Local mode
Stop-Process -Name python, node, uvicorn, npm -Force -ErrorAction SilentlyContinue 2>$null

$ROOT = (Get-Location).Path
$env:PYTHONPATH = $ROOT
$env:LITE_MODE = "true"

# Load .env into current process
Get-Content ".env" | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $eqIdx = $line.IndexOf("=")
        if ($eqIdx -gt 0) {
            $key = $line.Substring(0, $eqIdx).Trim()
            $val = $line.Substring($eqIdx + 1).Trim()
            [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
}

$env:MODEL_SERVICE_URL = $modelEndpoint

# Auto-install api-service deps
$apiReqFile = "backend\api-service\requirements.txt"
$apiStampFile = "backend\api-service\.deps_installed"
if (Test-Path $apiReqFile) {
    $apiReqHash = (Get-FileHash $apiReqFile -Algorithm MD5).Hash
    if (-not (Test-Path $apiStampFile) -or (Get-Content $apiStampFile -ErrorAction SilentlyContinue) -ne $apiReqHash) {
        Write-Host "Installing api-service dependencies..." -ForegroundColor Yellow
        python -m pip install -r $apiReqFile --quiet 2>&1 | Out-Null
        $apiReqHash | Out-File $apiStampFile -NoNewline
        Write-Host "  Done" -ForegroundColor Green
    } else {
        Write-Host "API service deps up-to-date (skipped)" -ForegroundColor Green
    }
}

# Auto-install frontend deps
if (-not (Test-Path "apps\frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location "apps\frontend"; npm install --silent 2>&1 | Out-Null; Pop-Location
    Write-Host "  Done" -ForegroundColor Green
} else {
    Write-Host "Frontend deps up-to-date (skipped)" -ForegroundColor Green
}

# Start core services
$apiCmd = "`$env:PYTHONPATH='$ROOT'; Set-Location '$ROOT\backend\api-service'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
$frontCmd = "Set-Location '$ROOT\apps\frontend'; npm run dev"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCmd
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontCmd

Write-Host ""
Write-Host "  === SummVi - Core Services Started ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Model Endpoint $modelEndpoint" -ForegroundColor Green
Write-Host "  Backend API    http://localhost:8000" -ForegroundColor Green
Write-Host "  Frontend       http://localhost:3000" -ForegroundColor Green
Write-Host "  Swagger Docs   http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
