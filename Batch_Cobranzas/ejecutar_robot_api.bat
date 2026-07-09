@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title Operaciones v1 - API

set "PROJECT_DIR=C:\Project\carteramora"
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "API_PORT=8000"

cd /d "%PROJECT_DIR%"

echo Levantando servicio API...
start "API_BOT_SERVICE_COBRANZAS" cmd /c "cd /d "%PROJECT_DIR%" && call "%VENV_DIR%\Scripts\activate" && python main.py api"

timeout /t 5 /nobreak > nul

set "LAST_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%API_PORT%" ^| findstr "LISTENING"') do (
    set "LAST_PID=%%P"
    goto CAPTURED
)

:CAPTURED
if "%LAST_PID%"=="" (
    echo No se pudo obtener el PID, pero el servicio deberia estar corriendo.
) else (
    echo PID del servicio: %LAST_PID%
    if not exist "%PROJECT_DIR%\pid" mkdir "%PROJECT_DIR%\pid"
    echo %LAST_PID% > "%PROJECT_DIR%\pid\api_bot.pid"
)

echo.
echo Servicio API levantado en http://localhost:%API_PORT%/
echo Ventana API_BOT_SERVICE_COBRANZAS abierta.
exit