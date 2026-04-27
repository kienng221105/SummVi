# ──────────────────────────────────────────────────────────────
# SummVi — Single-command Docker launcher
# Usage:  .\scripts\run_docker.ps1          (from any directory)
#         docker compose up --build         (from project root)
# ──────────────────────────────────────────────────────────────
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

Write-Host ""
Write-Host "  ╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║   SummVi  —  Starting All Services   ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Services:" -ForegroundColor Yellow
Write-Host "    • PostgreSQL   →  localhost:5432"
Write-Host "    • Backend API  →  http://localhost:8000"
Write-Host "    • Frontend     →  http://localhost:3000"
Write-Host "    • Swagger Docs →  http://localhost:8000/docs"
Write-Host ""
Write-Host "  Analytics endpoints:" -ForegroundColor Yellow
Write-Host "    • GET /analytics/topics"
Write-Host "    • GET /analytics/top-keywords"
Write-Host "    • GET /analytics/trends"
Write-Host "    • GET /analytics/summary-stats"
Write-Host ""

docker compose up --build
