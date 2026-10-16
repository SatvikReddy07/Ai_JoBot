# HSE Career Agent - Stop Script (PowerShell)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "Stopping HSE Career Agent services..." -ForegroundColor Yellow

# Kill backend via PID or port 8000
$BackendPidFile = Join-Path $ProjectRoot "data\backend.pid"
if (Test-Path $BackendPidFile) {
    $BackendPid = Get-Content $BackendPidFile
    Stop-Process -Id $BackendPid -Force -ErrorAction SilentlyContinue
    Remove-Item $BackendPidFile -Force -ErrorAction SilentlyContinue
}

# Kill frontend via PID
$FrontendPidFile = Join-Path $ProjectRoot "data\frontend.pid"
if (Test-Path $FrontendPidFile) {
    $FrontendPid = Get-Content $FrontendPidFile
    Stop-Process -Id $FrontendPid -Force -ErrorAction SilentlyContinue
    Remove-Item $FrontendPidFile -Force -ErrorAction SilentlyContinue
}

# Fallback cleanup for node processes on port 3000 or uvicorn on 8000
$UvicornProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*backend\venv*" }
if ($UvicornProcesses) {
    $UvicornProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
}

Write-Host "All HSE Career Agent services stopped successfully." -ForegroundColor Green
