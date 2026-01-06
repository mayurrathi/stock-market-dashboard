#!/bin/bash

# Kill any existing processes on port 8001
echo "Cleaning up port 8001..."
lsof -ti:8001 | xargs kill -9 2>/dev/null

# Install dependencies if needed
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Start the FastAPI server
echo "Starting Stock Market Dashboard on http://localhost:8001..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8001

