# Local Development Setup Guide

This guide explains how to set up and run the Lego Builder project locally without Docker.

## Prerequisites

### 1. Python 3.10+
Ensure Python 3.10 or higher is installed:
```bash
python3 --version
```

### 2. uv (Python Package Manager)
Install uv if not already installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart terminal
```

### 3. Node.js 20.9.0+
Install Node.js 20 or higher. Recommended: use nvm:
```bash
nvm install 20
nvm use 20
```

### 4. System Dependencies (Linux)
Install OpenGL and graphics libraries required for 3D rendering:
```bash
./install-deps.sh
```

Or manually:
```bash
sudo apt-get install -y libgl1 libglx-mesa0 libglib2.0-0 libxrender1 libxext6 libglu1-mesa libsm6 libosmesa6-dev
```

## Quick Start

### 1. Install System Dependencies
```bash
./install-deps.sh
```

### 2. Run Setup
```bash
./setup.sh
```

### 3. Configure Environment
Edit `Backend/.env` and add your `GOOGLE_API_KEY`:
```bash
nano Backend/.env
```

### 4. Start Development Servers
```bash
./run-all.sh
```

Or in separate terminals:
```bash
# Terminal 1: Backend
./run-backend.sh

# Terminal 2: Frontend
./run-frontend.sh
```

## Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

## Project Structure

```
Lego builder python/
├── Backend/                 # Python FastAPI backend
│   ├── .venv/              # Python virtual environment (created by setup.sh)
│   ├── main.py             # FastAPI entry point
│   ├── requirements.txt    # Python dependencies
│   └── .env                # Environment variables
├── Frontend/               # Next.js frontend
│   ├── node_modules/       # Node dependencies (created by setup.sh)
│   └── .env.local          # Frontend environment variables
├── setup.sh                # One-time setup script
├── run-backend.sh          # Start backend server
├── run-frontend.sh         # Start frontend server
├── run-all.sh              # Start both servers
└── install-deps.sh         # Install system dependencies
```

## Troubleshooting

### OpenGL Errors
If you see OpenGL-related errors, ensure all system dependencies are installed:
```bash
./install-deps.sh
```

### Playwright Issues
If Playwright fails, reinstall browsers:
```bash
cd Backend
source .venv/bin/activate
playwright install chromium
```

### Port Already in Use
Kill existing processes:
```bash
lsof -ti:8001 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

### Virtual Environment Not Found
Run the setup script:
```bash
./setup.sh
```

### Missing GOOGLE_API_KEY
Edit `Backend/.env` and add your API key:
```bash
GOOGLE_API_KEY=your_actual_api_key_here
```

## Development Workflow

1. Make changes to code
2. Backend auto-reloads on Python file changes
3. Frontend auto-reloads on TypeScript/React file changes
4. Test at http://localhost:3000
