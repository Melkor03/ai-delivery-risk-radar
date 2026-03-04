#!/bin/bash
# Delivery Risk Radar - Local Setup Script
# Run this from the project root directory

set -e

echo "🎯 Delivery Risk Radar - Setup Script"
echo "======================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo "✅ Node.js found: $(node --version)"

# Backend setup
echo ""
echo "📦 Setting up Backend..."
cd backend

# Check for .env
if [ ! -f .env ]; then
    echo "❌ .env file not found in backend/"
    echo "   Copy .env.example to .env and fill in your values"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install
source venv/bin/activate
echo "   Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo "✅ Backend ready"

# Frontend setup
echo ""
echo "📦 Setting up Frontend..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "   Installing npm dependencies..."
    npm install --silent
fi

echo "✅ Frontend ready"

echo ""
echo "======================================"
echo "🚀 Setup complete!"
echo ""
echo "To run the application:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend"
echo "    source venv/bin/activate"
echo "    uvicorn server:app --host 0.0.0.0 --port 8001 --reload"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend"
echo "    npm start"
echo ""
echo "Then open: http://localhost:3000"
echo "======================================"
