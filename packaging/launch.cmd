@echo off
rem Start Agora in Windows Terminal when available, otherwise in a sized UTF-8 console.
where wt >nul 2>nul && (start "" wt -w new --title Agora "%~dp0agora.exe" %* & exit /b)
chcp 65001 >nul
mode con cols=160 lines=45
"%~dp0agora.exe" %*
