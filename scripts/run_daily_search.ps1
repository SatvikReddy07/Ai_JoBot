# PowerShell Runner for HSE Career Agent Scheduled Search
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$PythonExe = Join-Path $ProjectRoot "backend\venv\Scripts\python.exe"
$SearchScript = Join-Path $ProjectRoot "scripts\run_scheduled_search.py"

Write-Host "[HSE Career Agent] Executing automated daily search..." -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot"
Write-Host "Python: $PythonExe"

& $PythonExe $SearchScript
$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0) {
    Write-Host "[HSE Career Agent] Search executed successfully." -ForegroundColor Green
} else {
    Write-Host "[HSE Career Agent] Search encountered errors (Exit code: $ExitCode)." -ForegroundColor Red
}
exit $ExitCode
