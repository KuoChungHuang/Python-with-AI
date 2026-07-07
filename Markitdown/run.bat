@echo off
setlocal

cd /d "%~dp0"

set "BASE_PYTHON=C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe"

if not exist "%BASE_PYTHON%" (
    echo Python not found: %BASE_PYTHON%
    echo Please install Python 3.12, or edit BASE_PYTHON in this file.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo First run: creating virtual environment, please wait...
    "%BASE_PYTHON%" -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Checking/installing dependencies (first run may take a while)...
"venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies. Please check your internet connection and try again.
    pause
    exit /b 1
)

echo Starting MarkItDown converter...
"venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo The program exited with an error.
    pause
)

endlocal
