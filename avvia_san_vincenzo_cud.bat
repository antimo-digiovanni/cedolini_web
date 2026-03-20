@echo off
set SCRIPT_DIR=%~dp0
set PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo Ambiente Python non trovato in .venv\Scripts\python.exe
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%SCRIPT_DIR%tools\san_vincenzo_cud_app.py"