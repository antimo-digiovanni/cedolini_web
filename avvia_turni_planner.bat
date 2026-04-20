@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
set "DEFAULT_WORKBOOK=C:\Users\antim\Il mio Drive\TURNI\Turni 2026\Week 13\Turni Lavoro.xlsx"

if not exist "%PYTHON%" (
    echo Ambiente Python non trovato: "%PYTHON%"
    pause
    exit /b 1
)

if exist "%DEFAULT_WORKBOOK%" (
    "%PYTHON%" -m turni_app "%DEFAULT_WORKBOOK%"
) else (
    "%PYTHON%" -m turni_app
)

endlocal