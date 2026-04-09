# Automate SummVi Startup
# Kill old processes
Stop-Process -Name python, node, uvicorn, npm -Force -ErrorAction SilentlyContinue
Start-Sleep -s 2

# Set Env
$ROOT = Get-Location
$env:PYTHONPATH = $ROOT.Path
$env:LITE_MODE = "true"
$env:NODE_OPTIONS = "--max-old-space-size=4096"

# Start Backend in new window
Write-Host "Starting Backend..."
Start-Process powershell -ArgumentList "-NoExit -Command cd apps/backend; python -m uvicorn app.main:app --port 8000 --reload"

# Start Frontend in new window
Write-Host "Starting Frontend..."
Start-Process powershell -ArgumentList "-NoExit -Command cd apps/frontend; npm run dev"

Write-Host "Done! Check the new windows for logs."
