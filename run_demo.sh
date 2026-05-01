#!/bin/bash
# ──────────────────────────────────────────────────────────
# Cortex Code Agent SDK — Interactive Demo Launcher
# ──────────────────────────────────────────────────────────
# Starts the Starlette backend and opens the interactive
# slide deck + live chat demo in your browser.
#
# Prerequisites:
#   pip install starlette uvicorn sse-starlette cortex-code-agent-sdk
#
# Usage:
#   chmod +x run_demo.sh && ./run_demo.sh
# ──────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=8765

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Cortex Code Agent SDK — Interactive Demo"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python dependencies
echo "Checking dependencies..."
python3 -c "import starlette, uvicorn, sse_starlette" 2>/dev/null || {
    echo "Installing missing dependencies..."
    pip3 install starlette uvicorn sse-starlette 2>/dev/null
}

python3 -c "import cortex_code_agent_sdk" 2>/dev/null || {
    echo "Installing Cortex Code Agent SDK..."
    pip3 install cortex-code-agent-sdk 2>/dev/null
}

echo "Dependencies OK."
echo ""

# Check if port is already in use
if lsof -i :"$PORT" >/dev/null 2>&1; then
    echo "Port $PORT is already in use."
    echo "Either stop the existing server or change PORT in this script."
    exit 1
fi

echo "Starting server on http://localhost:$PORT"
echo "Press Ctrl+C to stop."
echo ""

# Open browser after a short delay
(sleep 2 && open "http://localhost:$PORT" 2>/dev/null || true) &

# Start the server
cd "$SCRIPT_DIR"
python3 server.py
