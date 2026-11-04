$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (!(Test-Path 'backend\venv\Scripts\python.exe')) { py -3.12 -m venv backend\venv }
& .\backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
Push-Location frontend
try {
    npm ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    $env:NEXT_TELEMETRY_DISABLED = '1'
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
Write-Host 'Setup complete. Run START_HSE_AGENT.bat. Existing data is preserved.'
