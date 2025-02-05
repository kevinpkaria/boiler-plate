#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Kill any existing processes
pkill -f "uvicorn main:app"

# Clear old logs
echo "" > logs/backend.log

# Start backend with proper logging
echo "Starting backend server..."
uvicorn main:app --reload --log-level debug --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Save PID for later use
echo $BACKEND_PID > logs/backend.pid

# Wait for backend to start
sleep 2

# Check if backend started successfully
if ps -p $BACKEND_PID > /dev/null; then
    echo "Backend started successfully with PID: $BACKEND_PID"
    echo "View logs with: tail -f logs/backend.log"
    echo "Stop server with: kill \$(cat logs/backend.pid)"
    
    # Watch logs in real-time
    tail -f logs/backend.log
else
    echo "Failed to start backend server"
    exit 1
fi
