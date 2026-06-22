param(
    [int]$Port = 8001,
    [switch]$StopExisting,
    [string]$LogLevel = "debug"
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    if (-not $StopExisting) {
        Write-Host "Port $Port is already in use by PID $($listener.OwningProcess)." -ForegroundColor Yellow
        Write-Host "Run again with -StopExisting to stop it and restart Uvicorn in this terminal:" -ForegroundColor Yellow
        Write-Host "  .\scripts\run_backend_8001.ps1 -StopExisting" -ForegroundColor Cyan
        exit 1
    }

    Write-Host "Stopping existing backend on port $Port, PID $($listener.OwningProcess)..." -ForegroundColor Yellow
    Stop-Process -Id $listener.OwningProcess -Force
    Start-Sleep -Seconds 1
}

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Could not find venv Python at $python"
}

$env:PYTHONUNBUFFERED = "1"
$env:FASTAPI_BASE_URL = "http://127.0.0.1:$Port"

Write-Host "Starting Uvicorn on http://127.0.0.1:$Port with log level '$LogLevel'." -ForegroundColor Green
Write-Host "Logs will stream here. Press Ctrl+C to stop the backend." -ForegroundColor Green

& $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port --reload --log-level $LogLevel --access-log
