@echo off
cd /d "%~dp0"
echo Batch Image Tool - one-time setup
echo.

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create venv. Make sure Python is installed and on PATH.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
)

echo.
echo Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

if errorlevel 1 (
    echo pip install failed.
    pause
    exit /b 1
)

echo.
echo Setup complete. You can now double-click Launch.bat to run the app.
pause
