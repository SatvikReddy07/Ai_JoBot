@echo off
title Running HSE Career Agent Daily Search
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_daily_search.ps1"
pause
