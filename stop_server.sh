#!/bin/bash

# Navigate to the directory containing this script
cd "$(dirname "$0")"

PID_FILE="server.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping PDF OCR Dashboard Server (PID: $PID)..."
        kill "$PID"
        
        # Wait up to 5 seconds for it to exit
        for i in {1..5}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Server did not shut down, sending SIGKILL..."
            kill -9 "$PID"
        fi
        echo "Server stopped."
    else
        echo "Server process (PID: $PID) is not running."
    fi
    rm "$PID_FILE"
else
    # Fallback to check if a process is running on port 44683
    PORT_PID=$(lsof -t -i:44683 2>/dev/null)
    if [ ! -z "$PORT_PID" ]; then
        echo "Found process running on port 44683 (PID: $PORT_PID). Stopping it..."
        kill "$PORT_PID"
        sleep 1
        if ps -p "$PORT_PID" > /dev/null 2>&1; then
            kill -9 "$PORT_PID"
        fi
        echo "Server stopped."
    else
        echo "No server.pid file found and no process detected on port 44683."
    fi
fi
