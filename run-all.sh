#!/bin/bash
# run-all.sh - Start both Backend and Frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Start Backend in background
echo "Starting Backend..."
"$SCRIPT_DIR/run-backend.sh" &
BACKEND_PID=$!

# Give Backend time to start
sleep 3

# Start Frontend in background
echo "Starting Frontend..."
"$SCRIPT_DIR/run-frontend.sh" &
FRONTEND_PID=$!

# Handle cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo ""
echo "=== Both services running ==="
echo "Backend:  http://localhost:8001"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for either process to exit
wait
