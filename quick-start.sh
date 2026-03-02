#!/bin/bash
# ChopBet Quick Start Script
# This script starts both the backend and frontend servers

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           🏆 ChopBet - Quick Start Guide                    ║"
echo "║     AI-Powered Football & Basketball Predictions             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $(python --version | cut -d' ' -f2)"

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Node.js $(node --version)"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} npm $(npm --version)"

echo ""
echo "Environment setup..."

# Backend
if [ ! -d "backend/venv" ]; then
    echo "Creating Python virtual environment..."
    cd backend
    python -m venv venv
    cd ..
fi

echo -e "${GREEN}✓${NC} Backend virtual environment ready"

# Check .env
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠ backend/.env not found${NC}"
    echo "  Create .env with: DATABASE_URL, GEMINI_API_KEY, TAVILY_API_KEY, ADMIN_API_KEY"
else
    echo -e "${GREEN}✓${NC} backend/.env exists"
fi

# Frontend node_modules
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo -e "${GREEN}✓${NC} Frontend dependencies ready"

echo ""
echo "Starting servers..."
echo ""
echo "Backend will run at: http://localhost:8000"
echo "Frontend will run at: http://localhost:3000"
echo ""
echo -e "${YELLOW}In separate terminals, run:${NC}"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend"
echo "    source venv/bin/activate  # Windows: venv\\Scripts\\activate"
echo "    uvicorn main:app --reload"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend"
echo "    npm run dev"
echo ""
echo "Then visit: http://localhost:3000"
echo ""
