$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root
docker compose up --build
