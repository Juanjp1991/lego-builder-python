#!/bin/bash
# install-deps.sh - Install system dependencies for local development (Ubuntu/Debian)

set -e

echo "Installing system dependencies for OpenGL and graphics..."

sudo apt-get update
sudo apt-get install -y \
    libgl1 \
    libglx-mesa0 \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libglu1-mesa \
    libsm6 \
    libosmesa6-dev

echo ""
echo "System dependencies installed successfully!"
