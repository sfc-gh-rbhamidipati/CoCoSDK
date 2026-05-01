#!/bin/bash
cd "$(dirname "$0")"
PORT=8765

# Activate project venv if it exists
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Check if port is already in use — if so, just open the browser
if lsof -i :"$PORT" >/dev/null 2>&1; then
    echo "Server already running on port $PORT. Opening browser..."
    open "http://localhost:$PORT"
    exit 0
fi

echo "Starting Cortex Code Agent SDK — Interactive Demo..."
echo "Server: http://localhost:$PORT"
echo "Press Ctrl+C to stop."
echo ""

# Open browser after server has time to start
(sleep 2 && open "http://localhost:$PORT") &

# Start the server
python3 server.py
