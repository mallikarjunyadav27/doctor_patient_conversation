@echo off
REM Doctor-Patient Translator Startup Script for Windows

echo.
echo ================================
echo Doctor-Patient Translator
echo Real-Time Voice Translation App
echo ================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo [*] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo [*] Checking dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

REM Check for .env file
if not exist ".env" (
    echo.
    echo [!] .env file not found!
    echo [!] Please create .env file with your SONIOX_API_KEY
    echo.
    echo Example:
    echo   SONIOX_API_KEY=your_key_here
    echo   SONIOX_MODEL=stt-rt-v3
    echo.
    pause
    exit /b 1
)

REM Check for API key in .env
findstr /r "SONIOX_API_KEY.*=" .env >nul 2>&1
if errorlevel 1 (
    echo.
    echo [!] SONIOX_API_KEY not found in .env
    echo [!] Please add your API key to .env file
    pause
    exit /b 1
)

REM Start the server
echo.
echo [✓] Starting Doctor-Patient Translator Server...
echo [✓] Server will be available at: http://localhost:8000
echo [✓] Press Ctrl+C to stop the server
echo.

cd backend
python main.py

pause
