# Start FastAPI backend + React frontend (no Docker)
# Usage: .\start.ps1
# Requirements: .venv created, .env filled, Node.js installed, npm install done in frontend/

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

# --- Prerequisites check ---
if (-not (Test-Path "$Root\.env")) {
    Write-Error ".env missing - copy .env.example and fill in the values."
}
if (-not (Test-Path "$Root\.venv\Scripts\python.exe")) {
    Write-Error "Virtual environment missing - run: python -m venv .venv"
}
if (-not (Test-Path "$Root\frontend\node_modules")) {
    Write-Error "Frontend dependencies missing - run: cd frontend && npm install"
}

# --- Backend FastAPI ---
Write-Host "[1/2] Starting FastAPI backend (port 8000)..." -ForegroundColor Cyan
$backendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    & "$root\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
} -ArgumentList $Root

# Wait for backend to respond before starting frontend
$timeout = 30
$elapsed = 0
Write-Host "   Waiting for backend..." -NoNewline
while ($elapsed -lt $timeout) {
    Start-Sleep -Seconds 1
    $elapsed++
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/docs" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($resp.StatusCode -eq 200) { break }
    } catch {}
    Write-Host "." -NoNewline
}
Write-Host " OK" -ForegroundColor Green

# --- Frontend React (production preview mode) ---
Write-Host "[2/2] Building + starting React frontend (port 3000)..." -ForegroundColor Cyan
$frontendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location "$root\frontend"
    npm run build --silent 2>&1 | Out-Null
    npm run preview -- --port 3000 --host
} -ArgumentList $Root

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  App running:" -ForegroundColor Green
Write-Host "    API  : http://localhost:8000" -ForegroundColor Green
Write-Host "    Docs : http://localhost:8000/docs" -ForegroundColor Green
Write-Host "    UI   : http://localhost:3000" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Ctrl+C or .\stop.ps1 to stop" -ForegroundColor Yellow
Write-Host ""

# Save job IDs so stop.ps1 can find them
$backendJob.Id  | Out-File "$Root\.running_jobs" -Force
$frontendJob.Id | Out-File "$Root\.running_jobs" -Append

# Stream logs from both services
try {
    while ($true) {
        Receive-Job $backendJob  -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "[API] $_" }
        Receive-Job $frontendJob -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "[UI]  $_" }
        Start-Sleep -Seconds 2
    }
} finally {
    Stop-Job $backendJob, $frontendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob, $frontendJob -Force -ErrorAction SilentlyContinue
    Remove-Item "$Root\.running_jobs" -ErrorAction SilentlyContinue
    Write-Host "Services stopped." -ForegroundColor Yellow
}