#!/bin/bash
# run-backend.sh - Start the Backend FastAPI server

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/Backend"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "Starting Backend on http://localhost:8001"
echo "API docs available at http://localhost:8001/docs"
echo ""
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
