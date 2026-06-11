#!/bin/bash

# Navigate to the directory containing this script
cd "$(dirname "$0")"

# Set up local virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Ensure requirements are installed
echo "Installing/updating requirements..."
pip install -r requirements.txt

# Start the server in the background and save the PID
echo "Starting PDF OCR Dashboard Server in background..."
nohup python app.py --dashboard > pdf_ocr_server.log 2>&1 &
echo $! > server.pid
echo "Server started in background with PID $(cat server.pid)."
echo "Logs are being written to pdf_ocr_server.log"
