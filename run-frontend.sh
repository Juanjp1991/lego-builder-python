#!/bin/bash
# run-frontend.sh - Start the Frontend Next.js dev server

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/Frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Error: node_modules not found. Run ./setup.sh first."
    exit 1
fi

echo "Starting Frontend on http://localhost:3000"
echo ""
npm run dev
