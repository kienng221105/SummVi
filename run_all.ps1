# SummVi - Single-Command Startup
# Usage:  .\run_all.ps1          (from project root)

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

$choice = Read-Host "Run SummVi? (1: Local, 2: Docker)"

if ($choice -eq "2") {
    Write-Host ""
    Write-Host "  === SummVi - Starting All Services ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Services:" -ForegroundColor Yellow
    Write-Host "    PostgreSQL      localhost:5432"
    Write-Host "    Model Service   http://localhost:8001"
    Write-Host "    Backend API     http://localhost:8000"
    Write-Host "    Frontend        http://localhost:3000"
    Write-Host "    Swagger Docs    http://localhost:8000/docs"
    Write-Host ""
    docker compose up --build
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

# Auto-install model-service deps
$modelReqFile = "backend\model-service\requirements.txt"
$modelStampFile = "backend\model-service\.deps_installed"
if (Test-Path $modelReqFile) {
    $modelReqHash = (Get-FileHash $modelReqFile -Algorithm MD5).Hash
    if (-not (Test-Path $modelStampFile) -or (Get-Content $modelStampFile -ErrorAction SilentlyContinue) -ne $modelReqHash) {
        Write-Host "Installing model-service dependencies..." -ForegroundColor Yellow
        python -m pip install -r $modelReqFile --quiet 2>&1 | Out-Null
        $modelReqHash | Out-File $modelStampFile -NoNewline
        Write-Host "  Done" -ForegroundColor Green
    } else {
        Write-Host "Model service deps up-to-date (skipped)" -ForegroundColor Green
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

# Start all services
$modelCmd = "`$env:PYTHONPATH='$ROOT'; Set-Location '$ROOT\backend\model-service'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
$apiCmd = "`$env:PYTHONPATH='$ROOT'; Set-Location '$ROOT\backend\api-service'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
$frontCmd = "Set-Location '$ROOT\apps\frontend'; npm run dev"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $modelCmd
Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCmd
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontCmd

Write-Host ""
Write-Host "  === SummVi - All Services Started ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Model Service  http://localhost:8001" -ForegroundColor Green
Write-Host "  Backend API    http://localhost:8000" -ForegroundColor Green
Write-Host "  Frontend       http://localhost:3000" -ForegroundColor Green
Write-Host "  Swagger Docs   http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
