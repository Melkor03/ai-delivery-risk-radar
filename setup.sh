#!/bin/bash
# ============================================================
# Delivery Risk Radar — One-Command Setup
# Run from project root: ./setup.sh
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "🎯 Delivery Risk Radar — Setup"
echo "================================"

# ── Check prerequisites ──
echo ""
echo "Checking prerequisites..."

if ! command -v python3 &>/dev/null; then
  echo -e "${RED}❌ Python 3 not found. Install from https://python.org${NC}"; exit 1
fi
if ! command -v node &>/dev/null; then
  echo -e "${RED}❌ Node.js not found. Install from https://nodejs.org${NC}"; exit 1
fi
if ! command -v docker &>/dev/null; then
  echo -e "${YELLOW}⚠️  Docker not found — you'll need MongoDB running separately${NC}"
  SKIP_DOCKER=1
fi

echo -e "${GREEN}✅ Python $(python3 --version | cut -d' ' -f2)${NC}"
echo -e "${GREEN}✅ Node $(node --version)${NC}"

# ── MongoDB via Docker ──
if [ -z "$SKIP_DOCKER" ]; then
  echo ""
  echo "Starting MongoDB..."
  if ! docker ps | grep -q "risk_radar_mongo"; then
    docker run -d --name risk_radar_mongo -p 27017:27017 \
      --restart unless-stopped mongo:7 > /dev/null 2>&1 || \
    docker start risk_radar_mongo > /dev/null 2>&1 || true
  fi
  echo -e "${GREEN}✅ MongoDB running on port 27017${NC}"
fi

# ── Backend setup ──
echo ""
echo "Setting up Backend..."
cd backend

if [ ! -f ".env" ]; then
  cp .env.example .env 2>/dev/null || cat > .env << 'ENVEOF'
MONGO_URL=mongodb://localhost:27017
DB_NAME=risk_radar
JWT_SECRET=risk-radar-dev-secret-change-in-production
OPENAI_API_KEY=
CLICKUP_API_TOKEN=
HOST=0.0.0.0
PORT=8001
ENVEOF
  echo -e "${YELLOW}⚠️  Created backend/.env — add your OPENAI_API_KEY for AI analysis${NC}"
fi

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q
echo -e "${GREEN}✅ Backend ready${NC}"
cd ..

# ── Frontend setup ──
echo ""
echo "Setting up Frontend..."
cd frontend

if [ ! -f ".env" ]; then
  echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env
fi

if [ ! -d "node_modules" ]; then
  npm install --silent
fi
echo -e "${GREEN}✅ Frontend ready${NC}"
cd ..

# ── Seed demo data ──
echo ""
echo "Seeding demo data..."
cd backend
source venv/bin/activate
python seed_demo.py
cd ..

echo ""
echo "================================"
echo -e "${GREEN}🚀 Setup complete!${NC}"
echo ""
echo "Start the app with:"
echo ""
echo -e "  ${YELLOW}Terminal 1 (Backend):${NC}"
echo "    cd backend && source venv/bin/activate"
echo "    uvicorn server:app --host 0.0.0.0 --port 8001 --reload"
echo ""
echo -e "  ${YELLOW}Terminal 2 (Frontend):${NC}"
echo "    cd frontend && npm start"
echo ""
echo "  Then open: http://localhost:3000"
echo ""
echo "  Demo login:"
echo "    Email:    demo@riskradar.com"
echo "    Password: Demo@1234"
echo "================================"
