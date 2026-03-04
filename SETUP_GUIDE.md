# Delivery Risk Radar - Local Setup Guide

## Prerequisites

- **macOS** (tested on macOS)
- **Docker Desktop** - For local MongoDB
- **Node.js 18+** - For frontend
- **Python 3.10+** - For backend (Note: Python 3.14 requires additional fixes)

---

## Quick Start (5 minutes)

### Step 1: Start MongoDB with Docker

```bash
# Open Docker Desktop first (wait for it to fully start)
open -a Docker

# Wait 30 seconds, then run:
docker run -d --name mongodb -p 27017:27017 mongo:7
```

### Step 2: Start Backend

```bash
cd ~/Documents/ai-delivery-risk-radar-clickup/backend

# Activate virtual environment
source venv/bin/activate

# Start server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Keep this terminal open.

### Step 3: Start Frontend (New Terminal)

```bash
cd ~/Documents/ai-delivery-risk-radar-clickup/frontend
npm start
```

### Step 4: Access the App

Open http://localhost:3000 in your browser.

---

## First-Time Setup

### 1. Register an Account

- Go to http://localhost:3000
- Click "Create one" 
- Fill in your name, email, and password
- Click "Create account"

### 2. Configure ClickUp Integration

1. **Get your ClickUp API Token:**
   - Go to ClickUp → Settings → Apps
   - Scroll to "API Token" section
   - Click "Generate" or copy existing token

2. **Add token in Risk Radar:**
   - Go to Settings (left sidebar)
   - Paste your ClickUp API Token
   - Click "Test Connection"
   - Select your Workspace and Space
   - Click "Save Configuration"

### 3. Create a Project

1. Go to **Projects** → **New Project**
2. Enter project name (e.g., "Sprint 1 Analysis")
3. Fill in details and save

### 4. Sync ClickUp Data

1. Go to **Data Upload**
2. Select your project
3. Click **ClickUp** tab
4. Click **Sync Now**

### 5. Run Risk Analysis

1. Go to **Projects**
2. Click on your project
3. Click **Run Analysis**
4. View the risk radar and recommendations

---

## Daily Usage

### Starting the App

**Terminal 1 - MongoDB (if not running):**
```bash
docker start mongodb
```

**Terminal 2 - Backend:**
```bash
cd ~/Documents/ai-delivery-risk-radar-clickup/backend
source venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 3 - Frontend:**
```bash
cd ~/Documents/ai-delivery-risk-radar-clickup/frontend
npm start
```

### Stopping the App

- Press `Ctrl+C` in each terminal
- To stop MongoDB: `docker stop mongodb`

---

## Configuration Files

### Backend (.env)

Location: `~/Documents/ai-delivery-risk-radar-clickup/backend/.env`

```env
# MongoDB (local Docker)
MONGO_URL=mongodb://localhost:27017
DB_NAME=risk_radar

# JWT Secret (change in production)
JWT_SECRET=your-secret-key-here

# OpenAI API Key (optional - for AI-powered analysis)
OPENAI_API_KEY=sk-your-key-here
```

### Frontend (.env)

Location: `~/Documents/ai-delivery-risk-radar-clickup/frontend/.env`

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

---

## Troubleshooting

### "Cannot connect to MongoDB"
```bash
# Check if Docker is running
docker ps

# Start MongoDB if stopped
docker start mongodb

# Or recreate it
docker rm mongodb
docker run -d --name mongodb -p 27017:27017 mongo:7
```

### "Failed to create account" or bcrypt errors
```bash
cd ~/Documents/ai-delivery-risk-radar-clickup/backend
source venv/bin/activate
pip install bcrypt==4.0.1
```

### Frontend shows "Compiled with problems"
```bash
cd ~/Documents/ai-delivery-risk-radar-clickup/frontend
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
npm start
```

### ClickUp sync shows 0 tasks
1. Go to **Settings** → Verify ClickUp API token is saved
2. Make sure you selected the correct **Space**
3. Ensure your ClickUp lists have tasks with the correct statuses

### Port already in use
```bash
# Kill process on port 8001
lsof -ti:8001 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

---

## Project Structure

```
ai-delivery-risk-radar-clickup/
├── backend/
│   ├── server.py          # FastAPI application
│   ├── integrations.py    # ClickUp/Jira/Sheets integrations
│   ├── report_generator.py # PDF report generation
│   ├── requirements.txt   # Python dependencies
│   └── .env               # Environment variables
├── frontend/
│   ├── src/
│   │   ├── pages/         # React pages
│   │   ├── components/    # UI components
│   │   └── context/       # Auth context
│   ├── public/
│   └── package.json
└── README.md
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Create account |
| `/api/auth/login` | POST | Login |
| `/api/projects` | GET/POST | List/Create projects |
| `/api/projects/{id}/analyze` | POST | Run risk analysis |
| `/api/clickup/sync` | POST | Sync ClickUp data |
| `/api/reports/executive` | POST | Generate PDF report |

---

## Support

For issues, check the backend terminal for error messages. Most problems are related to:
1. MongoDB not running
2. Missing environment variables
3. Package version conflicts

---

*Built by Suresh Babu | Delivery Risk Radar v0.1*
