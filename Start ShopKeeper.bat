@echo off
title ShopKeeper
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo First-time setup — installing requirements, please wait...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

python run.py
pause
