# One-command GRIDSTATE demo for native Windows PowerShell.
# Ingests the committed sample data, builds the state graph, runs the
# discovery engine, then starts the API and frontend dev server.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== GRIDSTATE demo =="

Set-Location backend
if (-not (Test-Path .venv)) {
    Write-Host "Creating virtualenv..."
    python -m venv .venv
}
$venvPy = ".venv\Scripts\python.exe"

Write-Host "Installing backend dependencies..."
& $venvPy -m pip install --quiet --upgrade pip
& $venvPy -m pip install --quiet -r requirements.txt

Write-Host "Running ingestion + state graph + discovery engine (uses the committed DEMO sample unless backend\data\raw\pbp_<season>.parquet already exists)..."
& $venvPy scripts\run_pipeline.py 2022 2023

Write-Host "Starting API on http://localhost:8000 ..."
$apiProc = Start-Process -FilePath $venvPy -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -PassThru -WindowStyle Hidden

Set-Location ..\frontend
if (-not (Test-Path node_modules)) {
    Write-Host "Installing frontend dependencies..."
    npm install
}

Write-Host "Starting frontend on http://localhost:5173 ..."
$feProc = Start-Process -FilePath "npm" -ArgumentList "run", "dev", "--", "--port", "5173" -PassThru -WindowStyle Hidden

Write-Host ""
Write-Host "GRIDSTATE is running:"
Write-Host "  API:      http://localhost:8000"
Write-Host "  Frontend: http://localhost:5173"
Write-Host ""
Write-Host "To stop both processes:"
Write-Host "  Stop-Process -Id $($apiProc.Id),$($feProc.Id)"
