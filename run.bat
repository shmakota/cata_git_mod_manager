@echo off
SETLOCAL

REM Check if virtual environment exists
IF NOT EXIST ".venv\" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate the virtual environment
CALL .venv\Scripts\activate.bat

REM Install requests package
pip install requests

REM Run the Python script
python mod_manager\selector.py

