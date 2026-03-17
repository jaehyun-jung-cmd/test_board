@echo off
chcp 65001 > nul

echo === Bulletin Board Setup ===
echo.

set PYTHON=C:\Users\tjgud\AppData\Local\Programs\Python\Python311\python.exe

if not exist "%PYTHON%" (
    echo ERROR: Python not found at %PYTHON%
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
"%PYTHON%" -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create venv
    pause
    exit /b 1
)

echo [2/3] Installing packages...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo.
echo === Next Steps ===
echo 1. Start Docker DB : docker-compose up -d
echo 2. Create DB tables: python manage.py init_db
echo 3. Run server      : python manage.py runserver
echo.
pause
