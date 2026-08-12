@echo off
setlocal

cd /d "%~dp0"
title AI-Polyphite

echo Iniciando AI-Polyphite...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"

if errorlevel 1 (
    echo.
    echo No se pudo iniciar AI-Polyphite.
    echo Revisa el error mostrado arriba y vuelve a intentarlo.
    echo.
    pause
    exit /b 1
)

echo.
echo Abriendo el dashboard...
start "" "http://127.0.0.1:3000"

endlocal
exit /b 0
