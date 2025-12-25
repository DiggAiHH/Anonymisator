#!/bin/bash
# Quick start script for SecureDoc Flow

set -e

echo "=========================================="
echo "SecureDoc Flow - Quick Start"
echo "=========================================="
echo ""

# Check dependencies
echo "Checking dependencies..."
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed. Aborting." >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required but not installed. Aborting." >&2; exit 1; }

echo "✓ All dependencies found"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Python dependencies installed"
echo ""

# Install Node dependencies
echo "Installing Node.js dependencies..."
npm install > /dev/null 2>&1
echo "✓ Node.js dependencies installed"
echo ""

# Build TypeScript
echo "Building TypeScript..."
npm run build > /dev/null 2>&1
echo "✓ TypeScript built"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration before starting services"
    echo ""
fi

echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "To start the services:"
echo ""
echo "  Backend (Terminal 1):"
echo "    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "  MCP Server (Terminal 2):"
echo "    npm start"
echo ""
echo "Or use Docker Compose:"
echo "    docker-compose up"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo "MCP Server: http://localhost:3000"
echo ""
