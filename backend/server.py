from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
import bcrypt as _bcrypt_lib
import json
import csv
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
SECRET_KEY = os.environ.get('JWT_SECRET', 'delivery-risk-radar-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing


# Security
security = HTTPBearer()

app = FastAPI(title="Delivery Risk Radar API")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== MODELS ==============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "viewer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    team_lead: Optional[str] = ""
    team_size: Optional[int] = 0
    start_date: Optional[str] = ""
    target_end_date: Optional[str] = ""
    status: str = "active"

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    team_lead: str
    team_size: int
    start_date: str
    target_end_date: str
    status: str
    risk_level: str
    risk_score: int
    last_analyzed: Optional[str] = None
    created_at: str
    created_by: str

class RiskAssessment(BaseModel):
    id: str
    project_id: str
    risk_level: str  # HIGH, MEDIUM, LOW
    risk_score: int  # 0-100
    confidence: int  # 0-100
    risk_drivers: List[Dict[str, Any]]
    impact_prediction: Dict[str, Any]
    recommendations: List[str]
    narrative: str
    risk_dimensions: Dict[str, int]  # For radar chart
    created_at: str

class ManualEntryCreate(BaseModel):
    project_id: str
    entry_type: str  # status_report, meeting_notes, risk_register
    title: str
    content: str
    date: Optional[str] = ""

class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str  # info, warning, alert, success
    project_id: Optional[str] = None

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: str
    project_id: Optional[str]
    read: bool
    created_at: str

class JiraConfigCreate(BaseModel):
    instance_url: str
    user_email: str
    api_token: str
    board_id: Optional[int] = None

# ============== AUTH HELPERS ==============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _bcrypt_lib.checkpw(plain_password.encode(), hashed_password.encode())

def hash_password(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt(12)).decode()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ============== AUTH ENDPOINTS ==============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_access_token({"sub": user_id})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
            created_at=user_doc["created_at"]
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user["id"]})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            created_at=user["created_at"]
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        created_at=current_user["created_at"]
    )

# ============== PROJECT ENDPOINTS ==============

@api_router.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, current_user: dict = Depends(get_current_user)):
    project_id = str(uuid.uuid4())
    project_doc = {
        "id": project_id,
        "name": project.name,
        "description": project.description,
        "team_lead": project.team_lead,
        "team_size": project.team_size,
        "start_date": project.start_date,
        "target_end_date": project.target_end_date,
        "status": project.status,
        "risk_level": "NEUTRAL",
        "risk_score": 0,
        "last_analyzed": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await db.projects.insert_one(project_doc)
    
    return ProjectResponse(**{k: v for k, v in project_doc.items() if k != "_id"})

@api_router.get("/projects", response_model=List[ProjectResponse])
async def get_projects(current_user: dict = Depends(get_current_user)):
    projects = await db.projects.find({}, {"_id": 0}).to_list(1000)
    return [ProjectResponse(**p) for p in projects]

@api_router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**project)

@api_router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project: ProjectCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.projects.find_one({"id": project_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project.model_dump()
    await db.projects.update_one({"id": project_id}, {"$set": update_data})
    
    updated = await db.projects.find_one({"id": project_id}, {"_id": 0})
    return ProjectResponse(**updated)

@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.projects.delete_one({"id": project_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}

# ============== RISK ANALYSIS ENDPOINTS ==============

@api_router.post("/projects/{project_id}/analyze", response_model=RiskAssessment)
async def analyze_project_risk(project_id: str, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Gather all data for this project
    uploads = await db.data_uploads.find({"project_id": project_id}, {"_id": 0}).to_list(100)
    entries = await db.manual_entries.find({"project_id": project_id}, {"_id": 0}).to_list(100)
    
    # Get latest Jira sync data
    jira_sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "jira"},
        {"_id": 0},
        sort=[("created_at", -1)]
    )

    # Get latest ClickUp sync data
    clickup_sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup"},
        {"_id": 0},
        sort=[("created_at", -1)]
    )

    # Prepare context for AI analysis
    context = {
        "project": project,
        "uploads": uploads,
        "manual_entries": entries,
        "jira_data": jira_sync.get("data") if jira_sync else None,
        "clickup_data": clickup_sync.get("data") if clickup_sync else None,
        "sheets_data": [u for u in uploads if u.get("data_type", "").startswith("sheets_")]
    }
    
    # Perform AI analysis
    try:
        analysis = await perform_ai_risk_analysis(context)
    except Exception as e:
        logger.error(f"AI analysis failed: {str(e)}")
        # Fallback to rule-based analysis
        analysis = perform_rule_based_analysis(context)
    
    assessment_id = str(uuid.uuid4())
    assessment_doc = {
        "id": assessment_id,
        "project_id": project_id,
        "risk_level": analysis["risk_level"],
        "risk_score": analysis["risk_score"],
        "confidence": analysis["confidence"],
        "risk_drivers": analysis["risk_drivers"],
        "impact_prediction": analysis["impact_prediction"],
        "recommendations": analysis["recommendations"],
        "narrative": analysis["narrative"],
        "risk_dimensions": analysis["risk_dimensions"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.risk_assessments.insert_one(assessment_doc)
    
    # Update project with latest risk info
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {
            "risk_level": analysis["risk_level"],
            "risk_score": analysis["risk_score"],
            "last_analyzed": assessment_doc["created_at"]
        }}
    )
    
    return RiskAssessment(**{k: v for k, v in assessment_doc.items() if k != "_id"})

@api_router.get("/projects/{project_id}/assessments", response_model=List[RiskAssessment])
async def get_project_assessments(project_id: str, current_user: dict = Depends(get_current_user)):
    assessments = await db.risk_assessments.find(
        {"project_id": project_id}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return [RiskAssessment(**a) for a in assessments]

@api_router.get("/assessments/latest", response_model=List[RiskAssessment])
async def get_latest_assessments(current_user: dict = Depends(get_current_user)):
    # Get latest assessment for each project
    pipeline = [
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$project_id",
            "latest": {"$first": "$$ROOT"}
        }},
        {"$replaceRoot": {"newRoot": "$latest"}},
        {"$project": {"_id": 0}}
    ]
    assessments = await db.risk_assessments.aggregate(pipeline).to_list(100)
    return [RiskAssessment(**a) for a in assessments]

# ============== DATA UPLOAD ENDPOINTS ==============

@api_router.post("/uploads")
async def upload_data(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    data_type: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    content = await file.read()
    file_content = content.decode('utf-8')
    
    # Parse based on file type
    parsed_data = None
    if file.filename.endswith('.json'):
        parsed_data = json.loads(file_content)
    elif file.filename.endswith('.csv'):
        reader = csv.DictReader(io.StringIO(file_content))
        parsed_data = list(reader)
    else:
        parsed_data = {"raw_content": file_content}
    
    upload_id = str(uuid.uuid4())
    upload_doc = {
        "id": upload_id,
        "project_id": project_id,
        "filename": file.filename,
        "data_type": data_type,
        "data": parsed_data,
        "uploaded_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.data_uploads.insert_one(upload_doc)
    
    return {
        "id": upload_id,
        "filename": file.filename,
        "data_type": data_type,
        "records_count": len(parsed_data) if isinstance(parsed_data, list) else 1,
        "created_at": upload_doc["created_at"]
    }

@api_router.get("/uploads")
async def get_uploads(project_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if project_id:
        query["project_id"] = project_id
    
    uploads = await db.data_uploads.find(query, {"_id": 0, "data": 0}).to_list(100)
    return uploads

# ============== MANUAL ENTRY ENDPOINTS ==============

@api_router.post("/entries")
async def create_manual_entry(entry: ManualEntryCreate, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"id": entry.project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    entry_id = str(uuid.uuid4())
    entry_doc = {
        "id": entry_id,
        "project_id": entry.project_id,
        "entry_type": entry.entry_type,
        "title": entry.title,
        "content": entry.content,
        "date": entry.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.manual_entries.insert_one(entry_doc)
    
    return {k: v for k, v in entry_doc.items() if k != "_id"}

@api_router.get("/entries")
async def get_manual_entries(project_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if project_id:
        query["project_id"] = project_id
    
    entries = await db.manual_entries.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return entries

# ============== NOTIFICATION ENDPOINTS ==============

@api_router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(current_user: dict = Depends(get_current_user)):
    notifications = await db.notifications.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return [NotificationResponse(**n) for n in notifications]

@api_router.post("/notifications")
async def create_notification(notification: NotificationCreate, current_user: dict = Depends(get_current_user)):
    notif_id = str(uuid.uuid4())
    notif_doc = {
        "id": notif_id,
        "user_id": current_user["id"],
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "project_id": notification.project_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.notifications.insert_one(notif_doc)
    return {k: v for k, v in notif_doc.items() if k != "_id"}

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user["id"]},
        {"$set": {"read": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}

@api_router.put("/notifications/read-all")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    await db.notifications.update_many(
        {"user_id": current_user["id"]},
        {"$set": {"read": True}}
    )
    return {"message": "All notifications marked as read"}

# ============== DASHBOARD STATS ==============

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    total_projects = await db.projects.count_documents({})
    high_risk = await db.projects.count_documents({"risk_level": "HIGH"})
    medium_risk = await db.projects.count_documents({"risk_level": "MEDIUM"})
    low_risk = await db.projects.count_documents({"risk_level": "LOW"})
    
    recent_assessments = await db.risk_assessments.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).to_list(5)
    
    unread_notifications = await db.notifications.count_documents({
        "user_id": current_user["id"],
        "read": False
    })
    
    return {
        "total_projects": total_projects,
        "risk_distribution": {
            "high": high_risk,
            "medium": medium_risk,
            "low": low_risk,
            "neutral": total_projects - high_risk - medium_risk - low_risk
        },
        "recent_assessments": recent_assessments,
        "unread_notifications": unread_notifications
    }

# ============== SETTINGS / INTEGRATIONS ==============

@api_router.post("/settings/jira")
async def save_jira_config(config: JiraConfigCreate, current_user: dict = Depends(get_current_user)):
    config_doc = {
        "user_id": current_user["id"],
        "instance_url": config.instance_url,
        "user_email": config.user_email,
        "api_token": config.api_token,  # In production, encrypt this
        "board_id": config.board_id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.jira_configs.update_one(
        {"user_id": current_user["id"]},
        {"$set": config_doc},
        upsert=True
    )
    
    return {"message": "Jira configuration saved"}

@api_router.get("/settings/jira")
async def get_jira_config(current_user: dict = Depends(get_current_user)):
    config = await db.jira_configs.find_one({"user_id": current_user["id"]}, {"_id": 0, "api_token": 0})
    return config or {}

# ============== AI ANALYSIS FUNCTIONS ==============

async def perform_ai_risk_analysis(context: dict) -> dict:
    """Perform AI-powered risk analysis using OpenAI"""
    from openai import OpenAI
    import re
    
    api_key = os.environ.get('EMERGENT_LLM_KEY') or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.warning("AI API key not configured, using rule-based analysis")
        return perform_rule_based_analysis(context)
    
    client = OpenAI(api_key=api_key)
    
    system_message = """You are an expert delivery risk analyst. Analyze project data to identify risks and provide actionable insights.
        
You must respond with a valid JSON object containing:
- risk_level: "HIGH", "MEDIUM", or "LOW"
- risk_score: integer 0-100 (higher = more risk)
- confidence: integer 0-100
- risk_drivers: array of {name, severity, description}
- impact_prediction: {timeline_impact, cost_impact, quality_impact}
- recommendations: array of strings
- narrative: detailed analysis paragraph
- risk_dimensions: {scope_creep, dependency_failure, false_reporting, quality_collapse, burnout, vendor_risk} each 0-100

Respond ONLY with the JSON object, no other text."""
    
    # Prepare data summaries
    jira_summary = ""
    if context.get('jira_data'):
        jira = context['jira_data']
        jira_summary = f"""
Jira Data:
- Total Issues: {jira.get('summary', {}).get('total_issues', 0)}
- Blocked Issues: {jira.get('summary', {}).get('blocked_count', 0)}
- Average Velocity: {jira.get('summary', {}).get('avg_velocity', 0):.1f}
- Status Distribution: {json.dumps(jira.get('summary', {}).get('status_distribution', {}))}
- Sprints: {len(jira.get('sprints', []))}
"""
    
    clickup_summary = ""
    if context.get('clickup_data'):
        cu = context['clickup_data']
        clickup_summary = f"""
ClickUp Data:
- Total Tasks: {cu.get('summary', {}).get('total_tasks', 0)}
- Blocked Tasks: {cu.get('summary', {}).get('blocked_count', 0)}
- Overdue Tasks: {cu.get('summary', {}).get('overdue_count', 0)}
- Total Points: {cu.get('summary', {}).get('total_points', 0)}
- Completed Points: {cu.get('summary', {}).get('completed_points', 0)}
- Status Distribution: {json.dumps(cu.get('summary', {}).get('status_distribution', {}))}
- Lists: {cu.get('summary', {}).get('total_lists', 0)}
"""

    sheets_summary = ""
    if context.get('sheets_data'):
        sheets_summary = f"\nGoogle Sheets Data: {len(context['sheets_data'])} records imported"
    
    upload_details = []
    for upload in context.get('uploads', [])[:5]:
        if isinstance(upload.get('data'), list):
            upload_details.append({
                'type': upload.get('data_type'),
                'records': len(upload.get('data', [])),
                'sample': upload.get('data', [{}])[0] if upload.get('data') else {}
            })
    
    prompt = f"""Analyze this project for delivery risks:

Project: {json.dumps(context.get('project', {}), indent=2)}
{jira_summary}
{clickup_summary}
{sheets_summary}

Data Uploads: {len(context.get('uploads', []))} files
Upload Details: {json.dumps(upload_details, indent=2)}

Manual Entries: {len(context.get('manual_entries', []))} entries
Entry Content Summary:
{json.dumps([{'type': e.get('entry_type'), 'title': e.get('title'), 'content': e.get('content', '')[:500]} for e in context.get('manual_entries', [])[:5]], indent=2)}

Analyze all available data for risks including:
- Sprint spillover and velocity trends
- Blocked tickets and dependency issues
- Team capacity and burnout signals
- Scope creep indicators
- False-green reporting patterns

Provide a comprehensive risk assessment in the JSON format specified."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        response_text = response.choices[0].message.content
        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
    
    # Fallback
    return perform_rule_based_analysis(context)

def perform_rule_based_analysis(context: dict) -> dict:
    """Fallback rule-based risk analysis"""
    project = context.get('project', {})
    entries = context.get('manual_entries', [])
    
    # Simple heuristics
    risk_score = 30  # Base score
    risk_drivers = []
    
    # Check for risk keywords in entries
    risk_keywords = ['blocked', 'delayed', 'urgent', 'escalation', 'missed', 'overdue', 'risk']
    for entry in entries:
        content = entry.get('content', '').lower()
        for keyword in risk_keywords:
            if keyword in content:
                risk_score += 10
                risk_drivers.append({
                    "name": f"Risk indicator: {keyword}",
                    "severity": "medium",
                    "description": f"Found '{keyword}' in {entry.get('entry_type', 'entry')}"
                })
    
    risk_score = min(risk_score, 100)
    
    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "confidence": 60,
        "risk_drivers": risk_drivers[:3] or [{"name": "Insufficient data", "severity": "low", "description": "More data needed for accurate assessment"}],
        "impact_prediction": {
            "timeline_impact": "1-2 weeks potential delay",
            "cost_impact": "Within budget tolerance",
            "quality_impact": "Minor quality risks"
        },
        "recommendations": [
            "Add more data sources for comprehensive analysis",
            "Schedule regular status updates",
            "Review team capacity and workload"
        ],
        "narrative": f"Based on available data, {project.get('name', 'this project')} shows {risk_level.lower()} risk indicators. More data would improve analysis accuracy.",
        "risk_dimensions": {
            "scope_creep": min(risk_score + 10, 100),
            "dependency_failure": risk_score,
            "false_reporting": max(risk_score - 20, 0),
            "quality_collapse": risk_score,
            "burnout": max(risk_score - 10, 0),
            "vendor_risk": max(risk_score - 30, 0)
        }
    }

# ============== JIRA SYNC ENDPOINTS ==============

from integrations import JiraClient, GoogleSheetsClient, ClickUpClient, map_columns, detect_data_type, extract_spreadsheet_id

class JiraSyncRequest(BaseModel):
    project_id: str
    board_id: Optional[int] = None
    project_key: Optional[str] = None

@api_router.post("/jira/test-connection")
async def test_jira_connection(current_user: dict = Depends(get_current_user)):
    """Test Jira connection with saved credentials"""
    config = await db.jira_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="Jira not configured")
    
    client = JiraClient(
        instance_url=config["instance_url"],
        email=config["user_email"],
        api_token=config["api_token"]
    )
    
    result = client.test_connection()
    return result

@api_router.get("/jira/boards")
async def get_jira_boards(current_user: dict = Depends(get_current_user)):
    """Get available Jira boards"""
    config = await db.jira_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="Jira not configured")
    
    client = JiraClient(
        instance_url=config["instance_url"],
        email=config["user_email"],
        api_token=config["api_token"]
    )
    
    return client.get_boards()

@api_router.get("/jira/sprints/{board_id}")
async def get_jira_sprints(board_id: int, current_user: dict = Depends(get_current_user)):
    """Get sprints for a board"""
    config = await db.jira_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="Jira not configured")
    
    client = JiraClient(
        instance_url=config["instance_url"],
        email=config["user_email"],
        api_token=config["api_token"]
    )
    
    return client.get_sprints(board_id, state="active,closed,future")

@api_router.post("/jira/sync")
async def sync_jira_data(request: JiraSyncRequest, current_user: dict = Depends(get_current_user)):
    """Full sync of Jira data for a project"""
    config = await db.jira_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="Jira not configured")
    
    project = await db.projects.find_one({"id": request.project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    client = JiraClient(
        instance_url=config["instance_url"],
        email=config["user_email"],
        api_token=config["api_token"]
    )
    
    # Use configured board_id if not provided
    board_id = request.board_id or config.get("board_id")
    
    # Perform full sync
    sync_result = client.full_sync(board_id=board_id, project_key=request.project_key)
    
    if sync_result["success"]:
        # Store synced data
        sync_id = str(uuid.uuid4())
        sync_doc = {
            "id": sync_id,
            "project_id": request.project_id,
            "source": "jira",
            "board_id": board_id,
            "data": sync_result,
            "synced_by": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.data_syncs.insert_one(sync_doc)
        
        # Also create normalized data uploads for analysis
        if sync_result.get("issues"):
            normalized_issues = map_columns(sync_result["issues"])
            upload_doc = {
                "id": str(uuid.uuid4()),
                "project_id": request.project_id,
                "filename": "jira_issues_sync.json",
                "data_type": "jira_issues",
                "data": normalized_issues,
                "uploaded_by": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.data_uploads.insert_one(upload_doc)
        
        if sync_result.get("velocity"):
            normalized_velocity = map_columns(sync_result["velocity"])
            upload_doc = {
                "id": str(uuid.uuid4()),
                "project_id": request.project_id,
                "filename": "jira_velocity_sync.json",
                "data_type": "velocity_data",
                "data": normalized_velocity,
                "uploaded_by": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.data_uploads.insert_one(upload_doc)
        
        # Create notification
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "title": "Jira Sync Complete",
            "message": f"Synced {sync_result['summary'].get('total_issues', 0)} issues, {len(sync_result.get('sprints', []))} sprints",
            "type": "success",
            "project_id": request.project_id,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {
        "success": sync_result["success"],
        "summary": sync_result.get("summary", {}),
        "synced_at": sync_result.get("synced_at"),
        "error": sync_result.get("error")
    }

@api_router.get("/jira/sync-history/{project_id}")
async def get_jira_sync_history(project_id: str, current_user: dict = Depends(get_current_user)):
    """Get Jira sync history for a project"""
    syncs = await db.data_syncs.find(
        {"project_id": project_id, "source": "jira"},
        {"_id": 0, "data": 0}
    ).sort("created_at", -1).to_list(20)
    return syncs


# ============== GOOGLE SHEETS ENDPOINTS ==============

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

class GoogleSheetsConfigCreate(BaseModel):
    client_id: str
    client_secret: str

class GoogleSheetsSyncRequest(BaseModel):
    project_id: str
    spreadsheet_url: str
    sheet_name: Optional[str] = "Sheet1"
    column_mapping: Optional[Dict[str, str]] = None

@api_router.post("/settings/google-sheets")
async def save_google_sheets_config(config: GoogleSheetsConfigCreate, current_user: dict = Depends(get_current_user)):
    """Save Google Sheets OAuth config"""
    config_doc = {
        "user_id": current_user["id"],
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.google_sheets_configs.update_one(
        {"user_id": current_user["id"]},
        {"$set": config_doc},
        upsert=True
    )
    
    return {"message": "Google Sheets configuration saved"}

@api_router.get("/settings/google-sheets")
async def get_google_sheets_config(current_user: dict = Depends(get_current_user)):
    """Get Google Sheets config (without secret)"""
    config = await db.google_sheets_configs.find_one(
        {"user_id": current_user["id"]},
        {"_id": 0, "client_secret": 0}
    )
    return config or {}

@api_router.get("/oauth/sheets/login")
async def google_sheets_login(current_user: dict = Depends(get_current_user)):
    """Start Google Sheets OAuth flow"""
    from google_auth_oauthlib.flow import Flow
    from fastapi.responses import JSONResponse
    
    config = await db.google_sheets_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="Google Sheets not configured. Please add OAuth credentials first.")
    
    redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', 
        f"{os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')}/api/oauth/sheets/callback")
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=redirect_uri
    )
    
    auth_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    
    # Store state for verification
    await db.oauth_states.insert_one({
        "state": state,
        "user_id": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"auth_url": auth_url}

@api_router.get("/oauth/sheets/callback")
async def google_sheets_callback(code: str, state: str):
    """Handle Google Sheets OAuth callback"""
    from google_auth_oauthlib.flow import Flow
    from fastapi.responses import RedirectResponse
    import warnings
    
    # Verify state
    state_doc = await db.oauth_states.find_one({"state": state})
    if not state_doc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    
    user_id = state_doc["user_id"]
    await db.oauth_states.delete_one({"state": state})
    
    config = await db.google_sheets_configs.find_one({"user_id": user_id}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="Google Sheets not configured")
    
    redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI',
        f"{os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')}/api/oauth/sheets/callback")
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=redirect_uri
    )
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        flow.fetch_token(code=code)
    
    creds = flow.credentials
    
    # Store tokens
    token_doc = {
        "user_id": user_id,
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "expires_at": creds.expiry.isoformat() if creds.expiry else None,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.google_sheets_tokens.update_one(
        {"user_id": user_id},
        {"$set": token_doc},
        upsert=True
    )
    
    # Redirect to frontend settings page
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    return RedirectResponse(f"{frontend_url}/settings?sheets_connected=true")

@api_router.get("/oauth/sheets/status")
async def google_sheets_connection_status(current_user: dict = Depends(get_current_user)):
    """Check if Google Sheets is connected"""
    token = await db.google_sheets_tokens.find_one({"user_id": current_user["id"]}, {"_id": 0})
    return {"connected": token is not None}

async def get_google_sheets_credentials(user_id: str):
    """Get valid Google credentials for a user, refreshing if needed"""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GoogleRequest
    
    token = await db.google_sheets_tokens.find_one({"user_id": user_id}, {"_id": 0})
    if not token:
        return None
    
    creds = Credentials(
        token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        token_uri=token.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token["client_id"],
        client_secret=token["client_secret"]
    )
    
    # Check if expired and refresh
    if token.get("expires_at"):
        from datetime import datetime
        expires = datetime.fromisoformat(token["expires_at"].replace('Z', '+00:00'))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) >= expires:
            creds.refresh(GoogleRequest())
            # Update stored token
            await db.google_sheets_tokens.update_one(
                {"user_id": user_id},
                {"$set": {
                    "access_token": creds.token,
                    "expires_at": creds.expiry.isoformat() if creds.expiry else None
                }}
            )
    
    return creds

@api_router.post("/sheets/sync")
async def sync_google_sheet(request: GoogleSheetsSyncRequest, current_user: dict = Depends(get_current_user)):
    """Sync data from a Google Sheet"""
    creds = await get_google_sheets_credentials(current_user["id"])
    if not creds:
        raise HTTPException(status_code=400, detail="Google Sheets not connected. Please authorize first.")
    
    project = await db.projects.find_one({"id": request.project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        client = GoogleSheetsClient(creds)
        spreadsheet_id = extract_spreadsheet_id(request.spreadsheet_url)
        
        # Get metadata
        metadata = client.get_sheet_metadata(spreadsheet_id)
        
        # Read data
        range_name = request.sheet_name or "Sheet1"
        raw_data = client.read_sheet(spreadsheet_id, range_name)
        
        if not raw_data:
            return {"success": False, "error": "No data found in sheet"}
        
        # Normalize columns
        normalized_data = map_columns(raw_data, request.column_mapping)
        
        # Detect data type
        data_type = detect_data_type(normalized_data)
        
        # Store as upload
        upload_id = str(uuid.uuid4())
        upload_doc = {
            "id": upload_id,
            "project_id": request.project_id,
            "filename": f"google_sheet_{metadata.get('title', 'unknown')}.json",
            "data_type": f"sheets_{data_type}",
            "data": normalized_data,
            "source_url": request.spreadsheet_url,
            "sheet_name": range_name,
            "uploaded_by": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.data_uploads.insert_one(upload_doc)
        
        # Create notification
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "title": "Google Sheets Sync Complete",
            "message": f"Imported {len(normalized_data)} rows from '{metadata.get('title', 'Sheet')}'",
            "type": "success",
            "project_id": request.project_id,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "upload_id": upload_id,
            "records_imported": len(normalized_data),
            "detected_type": data_type,
            "columns_mapped": list(normalized_data[0].keys()) if normalized_data else [],
            "sheet_title": metadata.get("title")
        }
        
    except Exception as e:
        logger.error(f"Google Sheets sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/sheets/preview")
async def preview_google_sheet(
    spreadsheet_url: str,
    sheet_name: str = "Sheet1",
    current_user: dict = Depends(get_current_user)
):
    """Preview columns from a Google Sheet to help with mapping"""
    creds = await get_google_sheets_credentials(current_user["id"])
    if not creds:
        raise HTTPException(status_code=400, detail="Google Sheets not connected")
    
    try:
        client = GoogleSheetsClient(creds)
        spreadsheet_id = extract_spreadsheet_id(spreadsheet_url)
        
        metadata = client.get_sheet_metadata(spreadsheet_id)
        raw_data = client.read_sheet(spreadsheet_id, sheet_name)
        
        if not raw_data:
            return {"columns": [], "sample_data": [], "sheets": metadata.get("sheets", [])}
        
        columns = list(raw_data[0].keys())
        sample_data = raw_data[:3]
        detected_type = detect_data_type(raw_data)
        
        return {
            "title": metadata.get("title"),
            "sheets": metadata.get("sheets", []),
            "columns": columns,
            "sample_data": sample_data,
            "detected_type": detected_type,
            "row_count": len(raw_data)
        }
        
    except Exception as e:
        logger.error(f"Sheet preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== ENHANCED DATA UPLOAD WITH COLUMN MAPPING ==============

@api_router.post("/uploads/with-mapping")
async def upload_data_with_mapping(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    data_type: str = Form(...),
    column_mapping: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Upload file with custom column mapping"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    content = await file.read()
    file_content = content.decode('utf-8')
    
    # Parse based on file type
    parsed_data = None
    if file.filename.endswith('.json'):
        parsed_data = json.loads(file_content)
        if not isinstance(parsed_data, list):
            parsed_data = [parsed_data]
    elif file.filename.endswith('.csv'):
        reader = csv.DictReader(io.StringIO(file_content))
        parsed_data = list(reader)
    else:
        parsed_data = [{"raw_content": file_content}]
    
    # Apply column mapping
    mapping = json.loads(column_mapping) if column_mapping else None
    normalized_data = map_columns(parsed_data, mapping)
    
    # Detect data type if auto
    detected_type = detect_data_type(normalized_data) if data_type == "auto" else data_type
    
    upload_id = str(uuid.uuid4())
    upload_doc = {
        "id": upload_id,
        "project_id": project_id,
        "filename": file.filename,
        "data_type": detected_type,
        "data": normalized_data,
        "column_mapping_applied": mapping,
        "uploaded_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.data_uploads.insert_one(upload_doc)
    
    return {
        "id": upload_id,
        "filename": file.filename,
        "data_type": detected_type,
        "records_count": len(normalized_data),
        "columns": list(normalized_data[0].keys()) if normalized_data else [],
        "created_at": upload_doc["created_at"]
    }

@api_router.post("/uploads/preview-columns")
async def preview_file_columns(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Preview columns from an uploaded file"""
    content = await file.read()
    file_content = content.decode('utf-8')
    
    parsed_data = None
    if file.filename.endswith('.json'):
        parsed_data = json.loads(file_content)
        if not isinstance(parsed_data, list):
            parsed_data = [parsed_data]
    elif file.filename.endswith('.csv'):
        reader = csv.DictReader(io.StringIO(file_content))
        parsed_data = list(reader)
    else:
        return {"columns": [], "sample_data": [], "detected_type": "unknown"}
    
    if not parsed_data:
        return {"columns": [], "sample_data": [], "detected_type": "unknown"}
    
    columns = list(parsed_data[0].keys())
    detected_type = detect_data_type(parsed_data)
    
    return {
        "columns": columns,
        "sample_data": parsed_data[:3],
        "detected_type": detected_type,
        "row_count": len(parsed_data)
    }


# ============== PDF REPORT GENERATION ==============

from report_generator_v3 import generate_enhanced_executive_report

class ReportGenerateRequest(BaseModel):
    organization_name: Optional[str] = "Organization"
    include_projects: Optional[List[str]] = None  # None means all projects

@api_router.post("/reports/executive")
async def generate_executive_pdf_report(
    request: ReportGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate comprehensive executive PDF report"""
    
    # Fetch all projects
    query = {}
    if request.include_projects:
        query["id"] = {"$in": request.include_projects}
    
    projects = await db.projects.find(query, {"_id": 0}).to_list(100)
    
    if not projects:
        raise HTTPException(status_code=404, detail="No projects found")
    
    # Fetch latest assessments for each project
    assessments = []
    for project in projects:
        assessment = await db.risk_assessments.find_one(
            {"project_id": project["id"]},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        if assessment:
            assessments.append(assessment)
    
    # Fetch dashboard stats
    stats = {
        "total_projects": len(projects),
        "risk_distribution": {
            "high": len([p for p in projects if (p.get("risk_level") or "").upper() == "HIGH"]),
            "medium": len([p for p in projects if (p.get("risk_level") or "").upper() == "MEDIUM"]),
            "low": len([p for p in projects if (p.get("risk_level") or "").upper() == "LOW"]),
            "neutral": len([p for p in projects if (p.get("risk_level") or "").upper() not in ["HIGH", "MEDIUM", "LOW"]])
        }
    }
    
    # Generate PDF
    try:
        pdf_bytes = generate_enhanced_executive_report(
            projects=[project],
            assessments=assessments,

            organization_name=project.get("name", "Project Report")
        )
        
        # Log report generation
        await db.report_logs.insert_one({
            "id": str(uuid.uuid4()),
            "generated_by": current_user["id"],
            "report_type": "executive",
            "projects_included": [p["id"] for p in projects],
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        filename = f"Risk_Radar_Executive_Report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@api_router.post("/reports/project/{project_id}")
async def generate_project_pdf_report(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate PDF report for a single project"""
    
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Fetch all assessments for this project
    assessments = await db.risk_assessments.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(10)
    
    stats = {
        "total_projects": 1,
        "risk_distribution": {
            "high": 1 if (project.get("risk_level") or "").upper() == "HIGH" else 0,
            "medium": 1 if (project.get("risk_level") or "").upper() == "MEDIUM" else 0,
            "low": 1 if (project.get("risk_level") or "").upper() == "LOW" else 0,
            "neutral": 1 if (project.get("risk_level") or "").upper() not in ["HIGH", "MEDIUM", "LOW"] else 0
        }
    }
    
    try:
        # Get task data for enhanced report
        sync = await db.data_syncs.find_one(
            {"project_id": project_id, "source": "clickup", "data.tasks.0": {"$exists": True}},
            sort=[("created_at", -1)]
        )
        tasks = sync.get("data", {}).get("tasks", []) if sync else []
        
        pdf_bytes = generate_enhanced_executive_report(
            projects=[project],
            assessments=assessments,
            organization_name=project.get("name", "Project Report"),
            tasks=tasks
        )
        
        filename = f"Risk_Report_{project.get('name', 'Project').replace(' ', '_')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate project report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

@api_router.get("/reports/history")
async def get_report_history(current_user: dict = Depends(get_current_user)):
    """Get report generation history"""
    reports = await db.report_logs.find(
        {"generated_by": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    return reports


# ============== CLICKUP INTEGRATION ENDPOINTS ==============

class ClickUpConfigCreate(BaseModel):
    api_token: str
    team_id: Optional[str] = None
    space_id: Optional[str] = None

class ClickUpSyncRequest(BaseModel):
    project_id: str
    space_id: Optional[str] = None
    list_ids: Optional[List[str]] = None

@api_router.post("/settings/clickup")
async def save_clickup_config(config: ClickUpConfigCreate, current_user: dict = Depends(get_current_user)):
    """Save ClickUp configuration"""
    config_doc = {
        "user_id": current_user["id"],
        "api_token": config.api_token,  # In production, encrypt this
        "team_id": config.team_id,
        "space_id": config.space_id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    await db.clickup_configs.update_one(
        {"user_id": current_user["id"]},
        {"$set": config_doc},
        upsert=True
    )

    return {"message": "ClickUp configuration saved"}

@api_router.get("/settings/clickup")
async def get_clickup_config(current_user: dict = Depends(get_current_user)):
    """Get ClickUp config (without API token)"""
    config = await db.clickup_configs.find_one(
        {"user_id": current_user["id"]},
        {"_id": 0, "api_token": 0}
    )
    return config or {}

@api_router.post("/clickup/test-connection")
async def test_clickup_connection(current_user: dict = Depends(get_current_user)):
    """Test ClickUp connection with saved credentials"""
    config = await db.clickup_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="ClickUp not configured")

    cu_client = ClickUpClient(api_token=config["api_token"])
    result = cu_client.test_connection()
    return result

@api_router.get("/clickup/teams")
async def get_clickup_teams(current_user: dict = Depends(get_current_user)):
    """Get available ClickUp workspaces (teams)"""
    config = await db.clickup_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="ClickUp not configured")

    cu_client = ClickUpClient(api_token=config["api_token"])
    return cu_client.get_teams()

@api_router.get("/clickup/spaces/{team_id}")
async def get_clickup_spaces(team_id: str, current_user: dict = Depends(get_current_user)):
    """Get spaces for a ClickUp workspace"""
    config = await db.clickup_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="ClickUp not configured")

    cu_client = ClickUpClient(api_token=config["api_token"])
    return cu_client.get_spaces(team_id)

@api_router.get("/clickup/lists/{space_id}")
async def get_clickup_lists(space_id: str, current_user: dict = Depends(get_current_user)):
    """Get lists for a ClickUp space"""
    config = await db.clickup_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="ClickUp not configured")

    cu_client = ClickUpClient(api_token=config["api_token"])
    # Get lists from space directly and from folders
    all_lists = cu_client.get_lists(space_id)
    folders = cu_client.get_folders(space_id)
    for folder in folders:
        folder_lists = cu_client.get_lists(space_id, folder_id=folder["id"])
        all_lists.extend(folder_lists)
    return all_lists

@api_router.post("/clickup/sync")
async def sync_clickup_data(request: ClickUpSyncRequest, current_user: dict = Depends(get_current_user)):
    """Full sync of ClickUp data for a project"""
    config = await db.clickup_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="ClickUp not configured")

    project = await db.projects.find_one({"id": request.project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    space_id = request.space_id or config.get("space_id")
    if not space_id:
        raise HTTPException(status_code=400, detail="No space_id provided. Please select a space in settings or provide one.")

    cu_client = ClickUpClient(api_token=config["api_token"])

    # Perform full sync
    sync_result = cu_client.full_sync(
        space_id=space_id,
        list_ids=request.list_ids
    )

    if sync_result["success"]:
        # Store synced data
        sync_id = str(uuid.uuid4())
        sync_doc = {
            "id": sync_id,
            "project_id": request.project_id,
            "source": "clickup",
            "space_id": space_id,
            "data": sync_result,
            "synced_by": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.data_syncs.insert_one(sync_doc)

        # Also create normalized data uploads for analysis
        if sync_result.get("tasks"):
            normalized_tasks = map_columns(sync_result["tasks"])
            upload_doc = {
                "id": str(uuid.uuid4()),
                "project_id": request.project_id,
                "filename": "clickup_tasks_sync.json",
                "data_type": "clickup_tasks",
                "data": normalized_tasks,
                "uploaded_by": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.data_uploads.insert_one(upload_doc)

        # Create notification
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "title": "ClickUp Sync Complete",
            "message": f"Synced {sync_result['summary'].get('total_tasks', 0)} tasks from ClickUp",
            "type": "success",
            "project_id": request.project_id,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    return {
        "success": sync_result["success"],
        "summary": sync_result.get("summary", {}),
        "synced_at": sync_result.get("synced_at"),
        "error": sync_result.get("error")
    }

@api_router.get("/clickup/sync-history/{project_id}")
async def get_clickup_sync_history(project_id: str, current_user: dict = Depends(get_current_user)):
    """Get ClickUp sync history for a project"""
    syncs = await db.data_syncs.find(
        {"project_id": project_id, "source": "clickup"},
        {"_id": 0, "data": 0}
    ).sort("created_at", -1).to_list(20)
    return syncs


# ============== HEALTH CHECK ==============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@api_router.get("/")
async def root():
    return {"message": "Delivery Risk Radar API", "version": "1.0.0"}

# ============== ENHANCED ENDPOINTS ==============
import re

def parse_story_points_from_name(task_name: str):
    match = re.search(r'\[SP:(\d+)\]', task_name)
    if match:
        return int(match.group(1))
    return None

@api_router.get("/projects/{project_id}/task-analysis")
async def get_task_analysis(project_id: str, current_user: dict = Depends(get_current_user)):
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup", "data.tasks.0": {"$exists": True}},
        sort=[("created_at", -1)]
    )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        return {"summary": {"total_tasks": 0}, "tasks": [], "at_risk_tasks": []}
    
    tasks = sync["data"]["tasks"]
    total = len(tasks)
    
    task_list = []
    high_risk = 0
    medium_risk = 0
    overdue = 0
    blocked = 0
    completed = 0
    in_progress = 0
    total_points = 0
    completed_points = 0
    
    for t in tasks:
        status = (t.get('status') or '').lower()
        points = t.get('story_points') or 0
        
        import re
        if not points:
            match = re.search(r'\[SP:(\d+)\]', t.get('summary') or t.get('name', ''))
            if match:
                points = int(match.group(1))
        
        total_points += points
        
        if status in ['complete', 'done', 'closed', 'resolved']:
            completed += 1
            completed_points += points
        elif status in ['in progress', 'in review']:
            in_progress += 1
        
        if t.get('blocked'):
            blocked += 1
        
        risk_score = 0
        flags = []
        
        if t.get('blocked'):
            risk_score += 25
            flags.append({'type': 'blocked', 'message': 'Task is blocked'})
        
        if not t.get('assignees'):
            risk_score += 15
            flags.append({'type': 'unassigned', 'message': 'No assignee'})
        
        if not t.get('due_date') and status not in ['complete', 'done', 'closed']:
            risk_score += 15
            flags.append({'type': 'no_due_date', 'message': 'No due date set'})
        
        risk_level = 'HIGH' if risk_score >= 50 else 'MEDIUM' if risk_score >= 25 else 'LOW'
        
        if risk_level == 'HIGH':
            high_risk += 1
        elif risk_level == 'MEDIUM':
            medium_risk += 1
        
        assignees = t.get('assignees', [])
        assignee_names = [(a.get('username') or a.get('email', 'Unknown')) if isinstance(a, dict) else str(a) for a in assignees] if assignees else []
        
        task_list.append({
            'task_id': t.get('id'),
            'name': t.get('summary') or t.get('name'),
            'status': t.get('status', 'Unknown'),
            'risk_score': risk_score,
            'risk_level': risk_level,
            'flags': flags,
            'assignees': assignee_names,
            'due_date': t.get('due_date'),
            'story_points': points,
            'url': t.get('url')
        })
    
    task_list.sort(key=lambda x: x['risk_score'], reverse=True)
    
    return {
        "summary": {
            "total_tasks": total,
            "completed_tasks": completed,
            "in_progress_tasks": in_progress,
            "blocked_tasks": blocked,
            "overdue_tasks": overdue,
            "high_risk_tasks": high_risk,
            "medium_risk_tasks": medium_risk,
            "completion_percentage": int(completed/total*100) if total > 0 else 0,
            "total_points": total_points,
            "completed_points": completed_points,
            "remaining_points": total_points - completed_points,
            "overall_risk_level": "HIGH" if high_risk >= 2 else "MEDIUM" if high_risk >= 1 or medium_risk >= 2 else "LOW"
        },
        "tasks": task_list,
        "at_risk_tasks": [t for t in task_list if t['risk_level'] in ['HIGH', 'MEDIUM']][:10]
    }

@api_router.get("/projects/{project_id}/burndown")
async def get_burndown(project_id: str, current_user: dict = Depends(get_current_user)):
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup", "data.tasks.0": {"$exists": True}},
        sort=[("created_at", -1)]
    )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        return {"dates": [], "ideal": [], "actual": [], "total_points": 0, "completed_points": 0}
    
    tasks = sync["data"]["tasks"]
    
    # Parse story points from [SP:X] in summary
    import re
    total_points = 0
    completed_points = 0
    
    for t in tasks:
        summary = t.get('summary') or t.get('name') or ''
        match = re.search(r'\[SP:(\d+)\]', summary)
        points = int(match.group(1)) if match else 0
        total_points += points
        
        status = (t.get('status') or '').lower()
        if status in ['complete', 'done', 'closed', 'resolved']:
            completed_points += points
    
    # If no story points found, use task count
    if total_points == 0:
        total_points = len(tasks)
        completed_points = sum(1 for t in tasks if (t.get('status') or '').lower() in ['complete', 'done', 'closed'])
    
    # Generate 14-day sprint burndown
    sprint_days = 14
    today = datetime.now(timezone.utc)
    start_date = today - timedelta(days=7)  # Assume mid-sprint
    
    dates = []
    ideal = []
    actual = []
    
    for i in range(sprint_days + 1):
        date = start_date + timedelta(days=i)
        dates.append(date.strftime('%m/%d'))
        
        # Ideal: linear burndown
        ideal_remaining = total_points * (1 - i / sprint_days)
        ideal.append(round(ideal_remaining, 1))
        
        # Actual: only show up to today
        if date <= today:
            days_elapsed = i
            if days_elapsed > 0:
                progress = completed_points * i / 7  # Assume 7 days elapsed
                actual.append(round(total_points - min(progress, completed_points), 1))
            else:
                actual.append(float(total_points))
        else:
            actual.append(None)
    
    remaining = total_points - completed_points
    velocity = completed_points / 7 if completed_points > 0 else 0
    
    return {
        "dates": dates,
        "ideal": ideal,
        "actual": actual,
        "total_points": total_points,
        "completed_points": completed_points,
        "remaining_points": remaining,
        "velocity": round(velocity, 2),
        "days_remaining": 7,
        "on_track": remaining <= (total_points * 0.5)
    }


@api_router.get("/projects/{project_id}/standup")
async def get_standup(project_id: str, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"id": project_id})
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup", "data.tasks.0": {"$exists": True}},
        sort=[("created_at", -1)]
    )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        return None
    
    tasks = sync["data"]["tasks"]
    project_name = project.get("name", "Project") if project else "Project"
    
    completed_yesterday = []
    in_progress_today = []
    blockers = []
    at_risk = []
    
    for t in tasks:
        summary = t.get('summary') or t.get('name') or 'Unknown'
        status = (t.get('status') or '').lower()
        assignees = t.get('assignees', [])
        assignee = (assignees[0].get('username', 'Unassigned') if isinstance(assignees[0], dict) else str(assignees[0])) if assignees else 'Unassigned'
        
        task_info = {
            'name': summary,
            'assignee': assignee,
            'status': status.title(),
            'url': t.get('url')
        }
        
        if status in ['complete', 'done', 'closed']:
            completed_yesterday.append(task_info)
        elif status in ['in progress', 'in review', 'review']:
            in_progress_today.append(task_info)
        
        if t.get('blocked'):
            blockers.append({**task_info, 'reason': 'Task is blocked'})
        
        # At risk: no assignee or no due date
        if not assignees or not t.get('due_date'):
            at_risk.append(task_info)
    
    # Generate talking points
    talking_points = []
    total = len(tasks)
    done = len(completed_yesterday)
    in_prog = len(in_progress_today)
    
    if done > 0:
        talking_points.append(f"✅ {done} task(s) completed")
    if in_prog > 0:
        talking_points.append(f"🔄 {in_prog} task(s) in progress")
    if blockers:
        talking_points.append(f"🚫 {len(blockers)} blocker(s) need attention")
    if len(at_risk) > 2:
        talking_points.append(f"⚠️ {len(at_risk)} tasks missing assignee or due date")
    
    if not talking_points:
        talking_points.append("✓ All tasks on track")
    
    return {
        "date": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        "project_name": project_name,
        "completed_yesterday": completed_yesterday[:5],
        "in_progress_today": in_progress_today[:10],
        "blockers": blockers[:5],
        "at_risk_tasks": at_risk[:5],
        "key_metrics": {
            "total_tasks": total,
            "completed": done,
            "in_progress": in_prog,
            "completion_pct": int(done / total * 100) if total > 0 else 0
        },
        "talking_points": talking_points,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@api_router.get("/projects/{project_id}/trends")
async def get_trends(project_id: str, days: int = 14, current_user: dict = Depends(get_current_user)):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    snapshots = await db.risk_snapshots.find(
        {"project_id": project_id, "created_at": {"$gte": cutoff}}
    ).sort("created_at", 1).to_list(100)
    
    trends = []
    for snap in snapshots:
        trends.append({
            "date": snap.get("snapshot_date", snap.get("created_at", "")[:10]),
            "overall_score": snap.get("overall_score", 0),
            "task_count": snap.get("task_count", 0),
            "high_risk_count": snap.get("high_risk_count", 0)
        })
    
    return {"trends": trends, "period_days": days}


@api_router.get("/projects/{project_id}/dependencies")
async def get_dependencies(project_id: str, current_user: dict = Depends(get_current_user)):
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup", "data.tasks.0": {"$exists": True}},
        sort=[("created_at", -1)]
    )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        return {"nodes": [], "edges": [], "blocked_chains": []}
    
    tasks = sync["data"]["tasks"]
    nodes = []
    edges = []
    blocked_chains = []
    
    for t in tasks:
        summary = t.get('summary') or t.get('name') or 'Unknown'
        status = (t.get('status') or '').lower()
        assignees = t.get('assignees', [])
        
        # Calculate simple risk
        risk_score = 0
        if not assignees:
            risk_score += 15
        if not t.get('due_date'):
            risk_score += 15
        if t.get('blocked'):
            risk_score += 25
        
        risk_level = 'HIGH' if risk_score >= 40 else 'MEDIUM' if risk_score >= 15 else 'LOW'
        
        nodes.append({
            'id': t.get('key') or t.get('id'),
            'name': summary[:40],
            'status': status,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'assignee': (assignees[0].get("username", "Unassigned") if isinstance(assignees[0], dict) else str(assignees[0])) if assignees else "Unassigned",
            'blocked': t.get('blocked', False)
        })
        
        # Add edges from dependencies
        for dep in t.get('dependencies', []):
            edges.append({
                'from': dep.get('task_id'),
                'to': t.get('key') or t.get('id'),
                'type': dep.get('type', 'depends_on')
            })
            
            if t.get('blocked'):
                blocked_chains.append({
                    'blocked_task': summary[:30],
                    'blocking_task': dep.get('task_id'),
                    'blocking_status': 'unknown'
                })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "blocked_chains": blocked_chains[:10],
        "total_dependencies": len(edges),
        "blocked_count": sum(1 for n in nodes if n['blocked'])
    }
@api_router.post("/projects/{project_id}/snapshot")
async def create_snapshot(project_id: str, current_user: dict = Depends(get_current_user)):
    """Create a risk snapshot for trend tracking"""
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup", "data.tasks.0": {"$exists": True}},
        sort=[("created_at", -1)]
    )
    
    tasks = sync.get("data", {}).get("tasks", []) if sync else []
    total = len(tasks)
    high_risk = sum(1 for t in tasks if not t.get('assignees') and not t.get('due_date'))
    
    snapshot = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "overall_score": 30 if high_risk > 2 else 15,
        "task_count": total,
        "high_risk_count": high_risk,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.risk_snapshots.insert_one(snapshot)
    return {"message": "Snapshot created", "snapshot_id": snapshot["id"]}
# Include router

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# ============================================
# NOTIFICATION SETTINGS ENDPOINTS
# ============================================

@api_router.get("/settings/notifications")
async def get_notification_settings(current_user: dict = Depends(get_current_user)):
    """Get user notification settings"""
    settings = await db.notification_settings.find_one(
        {"user_id": current_user["id"]},
        {"_id": 0}
    )
    
    if not settings:
        # Return defaults
        return {
            "user_id": current_user["id"],
            "slack_enabled": False,
            "slack_webhook": "",
            "email_enabled": False,
            "email_frequency": "daily",
            "risk_threshold": 65,
            "alert_high_risk": True,
            "alert_overdue": True,
            "alert_blocked": True
        }
    
    return settings

@api_router.post("/settings/notifications")
async def save_notification_settings(
    settings: dict,
    current_user: dict = Depends(get_current_user)
):
    """Save user notification settings"""
    settings_doc = {
        "user_id": current_user["id"],
        "slack_enabled": settings.get("slack_enabled", False),
        "slack_webhook": settings.get("slack_webhook", ""),
        "email_enabled": settings.get("email_enabled", False),
        "email_frequency": settings.get("email_frequency", "daily"),
        "risk_threshold": settings.get("risk_threshold", 65),
        "alert_high_risk": settings.get("alert_high_risk", True),
        "alert_overdue": settings.get("alert_overdue", True),
        "alert_blocked": settings.get("alert_blocked", True),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.notification_settings.update_one(
        {"user_id": current_user["id"]},
        {"$set": settings_doc},
        upsert=True
    )
    
    return {"message": "Settings saved successfully", "settings": settings_doc}

app.include_router(api_router)
