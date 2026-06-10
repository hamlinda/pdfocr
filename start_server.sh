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

# Start the server for clients to access the dashboard
echo "Starting PDF OCR Dashboard Server..."
python app.py --dashboard
