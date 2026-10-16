# HSE Career Agent - Start Script (PowerShell)
$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$PythonExe = Join-Path $BackendDir "venv\Scripts\python.exe"

# Ensure environment paths are populated
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
$env:PYTHONPATH = $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         HSE CAREER AGENT - STARTING LOCAL SERVICES       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 0. Clean previous instances
$StopScript = Join-Path $ScriptDir "stop_app.ps1"
if (Test-Path $StopScript) {
    & $StopScript
}
Start-Sleep -Seconds 1

# 1. Start FastAPI Backend on 127.0.0.1:8000
Write-Host "[1/3] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
$BackendProcess = Start-Process -FilePath $PythonExe `
    -ArgumentList "-m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000" `
    -WorkingDirectory $ProjectRoot `
    -PassThru -WindowStyle Minimized

Set-Content -Path (Join-Path $ProjectRoot "data\backend.pid") -Value $BackendProcess.Id

# Wait briefly for backend to initialize
Start-Sleep -Seconds 2

# 2. Start Next.js Frontend on http://localhost:3000
Write-Host "[2/3] Starting Next.js Dashboard on http://localhost:3000..." -ForegroundColor Yellow
$FrontendProcess = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c npm start" `
    -WorkingDirectory $FrontendDir `
    -PassThru -WindowStyle Minimized

Set-Content -Path (Join-Path $ProjectRoot "data\frontend.pid") -Value $FrontendProcess.Id

# 3. Open Browser
Write-Host "[3/3] Opening Dashboard in default browser..." -ForegroundColor Green
Start-Sleep -Seconds 3
Start-Process "http://localhost:3000"

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  HSE Career Agent is now running!" -ForegroundColor Green
Write-Host "  Dashboard:   http://localhost:3000" -ForegroundColor White
Write-Host "  Backend API: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  To stop the application, run: scripts\stop_app.ps1" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Green
