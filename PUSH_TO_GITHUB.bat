@echo off
title HSE Career Agent - Push to GitHub
cd /d "%~dp0"
echo ===================================================
echo   HSE Career Agent - Push to GitHub
echo   Repository: https://github.com/SatvikReddy07/Ai_JoBot.git
echo ===================================================
echo.

set "GIT_EXE=C:\Users\631937\AppData\Local\Programs\Git\cmd\git.exe"
if not exist "%GIT_EXE%" set "GIT_EXE=git"

echo Pushing main branch to origin...
"%GIT_EXE%" push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ===================================================
    echo   SUCCESS! Pushed successfully to GitHub:
    echo   https://github.com/SatvikReddy07/Ai_JoBot
    echo ===================================================
) else (
    echo.
    echo ===================================================
    echo   Push encountered an error or needs login.
    echo ===================================================
)

echo.
pause
