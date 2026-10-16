# Register Windows Scheduled Task for Daily Search
param (
    [string]$Time = "08:00"
)

$TaskName = "HSE_Career_Agent_Daily_Search"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunnerScript = Join-Path $ScriptDir "run_daily_search.ps1"

Write-Host "Configuring Windows Task Scheduler for $TaskName at $Time daily..." -ForegroundColor Cyan

# Action: launch powershell with runner script
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RunnerScript`""

# Trigger: daily at specified time
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

# Settings: run only when network available, stop if running > 1 hr
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Unregister if already exists
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Register task for current user
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Automated daily search for HSE Leadership opportunities across India, Singapore, Europe, and Australia."

Write-Host "Scheduled task '$TaskName' successfully registered to run daily at $Time." -ForegroundColor Green
Write-Host "Note: Your Windows PC must be powered on or awake at scheduled time for execution." -ForegroundColor Yellow
