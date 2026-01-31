#!/bin/bash

# Doctor-Patient Translator Startup Script for Linux/macOS

echo ""
echo "================================"
echo "Doctor-Patient Translator"
echo "Real-Time Voice Translation App"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.8+ from https://www.python.org"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "[*] Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "[*] Checking dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "[!] .env file not found!"
    echo "[!] Please create .env file with your SONIOX_API_KEY"
    echo ""
    echo "Example:"
    echo "  SONIOX_API_KEY=your_key_here"
    echo "  SONIOX_MODEL=stt-rt-v3"
    echo ""
    exit 1
fi

# Check for API key in .env
if ! grep -q "SONIOX_API_KEY" .env; then
    echo ""
    echo "[!] SONIOX_API_KEY not found in .env"
    echo "[!] Please add your API key to .env file"
    exit 1
fi

# Start the server
echo ""
echo "[✓] Starting Doctor-Patient Translator Server..."
echo "[✓] Server will be available at: http://localhost:8000"
echo "[✓] Press Ctrl+C to stop the server"
echo ""

cd backend
python main.py
