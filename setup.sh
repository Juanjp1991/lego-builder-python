#!/bin/bash
# setup.sh - Initial setup for local development environment
# Run once after cloning the repository

set -e

echo "=== Lego Builder Local Development Setup ==="

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Install it with:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Install Node.js 20.9.0 or higher."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    echo "Error: Node.js 20.9.0+ required. Current: $(node -v)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Setup Backend
echo ""
echo "=== Setting up Backend ==="
cd "$SCRIPT_DIR/Backend"

# Create virtual environment with uv
echo "Creating Python virtual environment..."
uv venv --python 3.10

# Install Python dependencies
echo "Installing Python dependencies..."
uv pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright Chromium browser..."
source .venv/bin/activate
playwright install chromium
deactivate

# Create .env if not exists
if [ ! -f .env ]; then
    echo "Creating Backend/.env from template..."
    cat > .env << 'EOF'
GOOGLE_API_KEY=your_api_key_here
OUTPUT_DIR=outputs
RAG_PERSIST_DIRECTORY=rag_db/development
EOF
    echo "WARNING: Please edit Backend/.env and add your GOOGLE_API_KEY"
fi

# Create outputs directory if not exists
mkdir -p outputs

cd "$SCRIPT_DIR"

# Setup Frontend
echo ""
echo "=== Setting up Frontend ==="
cd "$SCRIPT_DIR/Frontend"

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

# Create .env.local if not exists
if [ ! -f .env.local ]; then
    echo "Creating Frontend/.env.local..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8001" > .env.local
fi

cd "$SCRIPT_DIR"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Before running, ensure you have installed system dependencies:"
echo "  ./install-deps.sh"
echo ""
echo "To start development:"
echo "  ./run-backend.sh    # In one terminal"
echo "  ./run-frontend.sh   # In another terminal"
echo ""
echo "Or run both simultaneously:"
echo "  ./run-all.sh"
