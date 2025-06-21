@echo off
setlocal

:: Check for argument
if "%~1"=="" (
    echo Usage: %~nx0 path\to\mod_folder
    exit /b 1
)

set "MOD_PATH=%~1"

:: Optional: Create virtual environment (commented out)
:: if not exist "venv" (
::     python -m venv venv
:: )

:: Optional: Activate virtual environment (commented out)
:: call venv\Scripts\activate.bat

:: Optional: Install dependencies (commented out)
:: pip install -r requirements.txt

:: Run the mod viewer
python mod_viewer.py "%MOD_PATH%"