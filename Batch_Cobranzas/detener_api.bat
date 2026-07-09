@echo off
setlocal enabledelayedexpansion

set "PROJECT_DIR=C:\Project\carteramora"
set "PID_FILE=%PROJECT_DIR%\pid\api_bot.pid"
set "API_PORT=8000"

echo ===== Deteniendo API Carteramora =====

:: 1. Matar por PID (y TODO su árbol)
if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    if defined PID (
        echo [1] Matando PID !PID! y su arbol...
        taskkill /PID !PID! /F /T >nul 2>&1
        del "%PID_FILE%"
    )
)

:: 2. Matar por puerto
echo [2] Buscando puerto %API_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%API_PORT%" ^| findstr "LISTENING"') do (
    echo     Matando PID %%a...
    taskkill /PID %%a /F /T >nul 2>&1
)

:: 3. Forzar cierre del CMD (clave)
echo [3] Cerrando ventana CMD del API...
for /f "tokens=2" %%a in ('tasklist /v ^| findstr API_BOT_SERVICE_COBRANZA') do (
    taskkill /PID %%a /F /T >nul 2>&1
)

echo ===== API detenida correctamente =====
timeout /t 3 >nul
exit