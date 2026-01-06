#!/bin/bash
# Restart script for Stock Market Dashboard

echo "🔄 Restarting Stock Market Dashboard..."

# Kill any existing server processes on port 8001
echo "Stopping existing processes..."
lsof -ti:8001 | xargs kill -9 2>/dev/null || true

# Wait a moment for ports to be freed
sleep 2

# Navigate to project directory and launch
cd "$(dirname "$0")"

echo "Starting server..."
./launch.sh
