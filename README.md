# Delivery Risk Radar

**AI-Powered Early Warning System for Enterprise Delivery Management**

Delivery Risk Radar is an intelligent platform that continuously monitors delivery signals and answers the critical question: *"Which projects/teams are likely to fail in the next 30–90 days—and why?"*

Unlike traditional PMO dashboards that show what happened, Risk Radar predicts what's going to break next.

![Risk Radar Dashboard](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![AI Powered](https://img.shields.io/badge/AI-GPT--5.2-blue)
![License](https://img.shields.io/badge/License-Proprietary-red)

---

## 🎯 What Problem Does It Solve?

Enterprises typically discover delivery failure **too late**:
- Deadlines are missed
- Scope has ballooned
- Customers are already escalated
- Leadership loses confidence

**The real problem**: Enterprises have visibility, but not foresight.

Traditional dashboards show velocity, sprint completion, and tickets closed. But they don't detect:
- Hidden dependency risks
- Team burnout signals
- Political delays
- Requirement churn
- Silent scope creep
- False-green reporting

**Risk Radar surfaces these before they explode.**

---

## 🚀 Key Features

### 1. AI-Powered Risk Analysis (GPT-5.2)
- **6 Risk Dimensions**: Scope Creep, Dependency Failure, False Reporting, Quality Collapse, Team Burnout, Vendor Risk
- **Risk Score (0-100%)**: Quantified delivery health with confidence levels
- **AI-Generated Narratives**: Plain English explanations of risk drivers
- **Actionable Recommendations**: Specific interventions for each risk

### 2. Multi-Source Data Integration

| Source | Data Type | Status |
|--------|-----------|--------|
| **Jira** | Sprints, Issues, Velocity, Blocked Tickets | ✅ Full Sync |
| **Google Sheets** | Custom spreadsheets with flexible column mapping | ✅ OAuth Integration |
| **CSV/JSON Files** | Jira exports, risk registers, metrics | ✅ Auto-detection |
| **Manual Entry** | Status reports, meeting notes, escalations | ✅ Available |

### 3. Flexible Column Mapping
Works with ANY column headers from your data sources:
- `Story Points`, `story_points`, `SP`, `Points` → all mapped correctly
- `Assignee`, `assigned_to`, `Owner` → normalized automatically
- 50+ field variations supported across all risk dimensions

### 4. Executive PDF Reports
Boardroom-ready reports including:
- Executive Summary with risk distribution charts
- Critical project deep-dives with AI analysis
- Impact predictions (timeline, cost, quality)
- Strategic recommendations
- Risk dimension analysis
- Methodology appendix

### 5. Real-Time Dashboard
- Risk Radar visualization (6-axis spider chart)
- Project portfolio with risk badges (HIGH/MEDIUM/LOW)
- Trend indicators and historical tracking
- Alert system for high-risk projects

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                        │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐          │
│  │Dashboard│ │ Projects │ │ Reports │ │Settings │          │
│  └────┬────┘ └────┬─────┘ └────┬────┘ └────┬────┘          │
└───────┼───────────┼────────────┼───────────┼────────────────┘
        │           │            │           │
        ▼           ▼            ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                         │
│  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐       │
│  │ Risk Analysis│ │  Integrations │ │ PDF Reports  │       │
│  │   (GPT-5.2)  │ │ Jira/Sheets   │ │  Generator   │       │
│  └──────────────┘ └───────────────┘ └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                      MongoDB                                 │
│  Projects │ Assessments │ Uploads │ Users │ Notifications   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Risk Dimensions Explained

| Dimension | What It Detects | Signals |
|-----------|-----------------|---------|
| **Scope Creep** | Uncontrolled scope expansion | Backlog additions, changing acceptance criteria, reopened stories |
| **Dependency Failure** | External blockers | Blocked tickets, waiting-on-external status, approval loops |
| **False Reporting** | Status vs reality gap | Green reports with declining velocity, repeated unresolved risks |
| **Quality Collapse** | Stability degradation | Bug spikes, regression increases, hotfix frequency |
| **Team Burnout** | Unsustainable workload | Overcommitment, increasing cycle times, late sprint closures |
| **Vendor Risk** | Third-party issues | Vendor delays, missed milestones, SLA breaches |

---

## 🔧 Setup & Configuration

### Prerequisites
- Node.js 18+
- Python 3.10+
- MongoDB 6.0+

### Environment Variables

**Backend (`/app/backend/.env`)**
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="risk_radar"
EMERGENT_LLM_KEY=your_openai_key
JWT_SECRET=your_jwt_secret
```

**Frontend (`/app/frontend/.env`)**
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

### Running Locally

```bash
# Backend
cd /app/backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd /app/frontend
yarn install
yarn start
```

---

## 📖 User Guide

### 1. Create a Project
Navigate to **Projects** → **New Project** → Enter details (name, team lead, dates)

### 2. Import Data

**Option A: Jira Sync**
1. Go to **Settings** → Configure Jira credentials
2. Go to **Data Upload** → **Jira Sync** → Click **Sync Now**

**Option B: Google Sheets**
1. Go to **Settings** → Configure Google OAuth
2. Go to **Data Upload** → **Google Sheets** → Paste URL → **Import**

**Option C: File Upload**
1. Go to **Data Upload** → **File Upload**
2. Drag & drop CSV/JSON files

**Option D: Manual Entry**
1. Go to **Data Upload** → **Manual Entry**
2. Add status reports, meeting notes, or risk register entries

### 3. Run AI Analysis
Open any project → Click **Run Analysis** → View AI-generated insights

### 4. Generate Reports
Go to **Reports** → Select projects → **Generate Executive Report** → Download PDF

---

## 📑 API Reference

### Authentication
```bash
POST /api/auth/register  # Create account
POST /api/auth/login     # Get JWT token
GET  /api/auth/me        # Get current user
```

### Projects
```bash
GET    /api/projects              # List all projects
POST   /api/projects              # Create project
GET    /api/projects/{id}         # Get project details
PUT    /api/projects/{id}         # Update project
DELETE /api/projects/{id}         # Delete project
POST   /api/projects/{id}/analyze # Run AI risk analysis
```

### Data Import
```bash
POST /api/jira/sync              # Full Jira sync
POST /api/sheets/sync            # Import from Google Sheets
POST /api/uploads/with-mapping   # Upload file with column mapping
POST /api/entries                # Create manual entry
```

### Reports
```bash
POST /api/reports/executive         # Generate executive PDF
POST /api/reports/project/{id}      # Generate single project PDF
GET  /api/reports/history           # Get report generation history
```

---

## 🎨 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Tailwind CSS, Shadcn/UI, Recharts |
| Backend | FastAPI, Python 3.10 |
| Database | MongoDB |
| AI | OpenAI GPT-5.2 (via Emergent Integrations) |
| PDF | ReportLab |
| Auth | JWT (python-jose) |

---

## 🔐 Security

- JWT-based authentication with 7-day token expiry
- Password hashing with bcrypt
- API tokens stored securely (Jira, Google OAuth)
- Reports marked CONFIDENTIAL with access logging
- CORS configured for production environments

---

## 📈 Roadmap

### Completed ✅
- [x] AI-powered risk analysis (GPT-5.2)
- [x] 6-dimension risk radar visualization
- [x] Jira full sync integration
- [x] Google Sheets integration with OAuth
- [x] Flexible column mapping
- [x] Executive PDF report generation
- [x] Project portfolio management
- [x] In-app notifications

### Coming Soon 🚧
- [ ] Email notifications (SendGrid)
- [ ] Slack alerts integration
- [ ] Scheduled report delivery
- [ ] Historical trend analysis
- [ ] Azure DevOps integration
- [ ] Role-based access control

---

## 🤝 Support

For enterprise support and custom integrations, contact your delivery team.

---

## 📄 License

Proprietary software. All rights reserved.

---

*Built for enterprise delivery excellence. Predict. Prevent. Perform.*
