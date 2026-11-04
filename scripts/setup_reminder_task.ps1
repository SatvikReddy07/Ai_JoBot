param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$TaskName = 'HSE_Career_Agent_Followups'
if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    exit
}
$Python = Join-Path $Root 'backend\venv\Scripts\python.exe'
$Runner = Join-Path $PSScriptRoot 'run_followup_reminders.py'
$Action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Runner`"" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15)
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
$Principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force -Description 'Local HSE application reminders; no messages sent.'
Write-Host 'Reminders run every 15 minutes while you are signed in and the PC is awake. Quiet hours: 22:00–07:00.'
