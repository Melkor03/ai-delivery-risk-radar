# enhanced_endpoints.py - New endpoints for Phase 1-3 features
# Add these to server.py

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel
import re
import json


# ============== MODELS ==============

class TaskRiskAnalysis(BaseModel):
    task_id: str
    name: str
    status: str
    risk_score: int
    risk_level: str
    flags: List[dict]
    assignees: List[str]
    due_date: Optional[str]
    story_points: Optional[int]
    list_name: Optional[str]


class SprintBurndownData(BaseModel):
    dates: List[str]
    ideal: List[float]
    actual: List[float]
    total_points: int
    completed_points: int
    remaining_points: int
    velocity: float


class RiskTrendData(BaseModel):
    date: str
    overall_score: int
    dimensions: Dict[str, int]
    task_count: int
    high_risk_count: int


class StandupSummary(BaseModel):
    date: str
    completed_yesterday: List[dict]
    in_progress_today: List[dict]
    blockers: List[dict]
    at_risk_tasks: List[dict]
    key_metrics: dict
    talking_points: List[str]


# ============== HELPER FUNCTIONS ==============

def parse_story_points(task_name: str) -> Optional[int]:
    """Extract story points from task name like [SP:5]"""
    match = re.search(r'\[SP:(\d+)\]', task_name)
    if match:
        return int(match.group(1))
    return None


def calculate_task_risk(task: dict) -> dict:
    """Calculate individual task risk score and flags"""
    score = 0
    flags = []
    now = datetime.now(timezone.utc)
    
    # Check overdue
    due_date = task.get('due_date')
    if due_date:
        try:
            if isinstance(due_date, str):
                due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            elif isinstance(due_date, (int, float)):
                due_dt = datetime.fromtimestamp(due_date/1000, tz=timezone.utc)
            else:
                due_dt = None
            
            if due_dt:
                status = (task.get('status') or '').lower()
                if status not in ['complete', 'done', 'closed', 'resolved']:
                    if due_dt < now:
                        days_overdue = (now - due_dt).days
                        score += min(40, 20 + days_overdue * 5)
                        flags.append({
                            'type': 'overdue',
                            'severity': 'high',
                            'message': f'Overdue by {days_overdue} day(s)',
                            'days': days_overdue
                        })
                    elif due_dt < now + timedelta(days=2):
                        score += 10
                        flags.append({
                            'type': 'due_soon',
                            'severity': 'medium',
                            'message': 'Due within 2 days'
                        })
        except Exception:
            pass
    else:
        status = (task.get('status') or '').lower()
        if status not in ['complete', 'done', 'closed', 'resolved', 'backlog']:
            score += 15
            flags.append({
                'type': 'no_due_date',
                'severity': 'medium',
                'message': 'No due date set'
            })
    
    # Check blocked
    if task.get('blocked'):
        score += 25
        flags.append({
            'type': 'blocked',
            'severity': 'high',
            'message': 'Task is blocked'
        })
    
    # Check unassigned
    assignees = task.get('assignees', [])
    if not assignees:
        score += 15
        flags.append({
            'type': 'unassigned',
            'severity': 'medium',
            'message': 'No assignee'
        })
    
    # Check stale
    updated = task.get('date_updated')
    if updated:
        try:
            if isinstance(updated, str):
                updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            elif isinstance(updated, (int, float)):
                updated_dt = datetime.fromtimestamp(updated/1000, tz=timezone.utc)
            else:
                updated_dt = None
            
            if updated_dt:
                days_stale = (now - updated_dt).days
                if days_stale > 7:
                    score += 10
                    flags.append({
                        'type': 'stale',
                        'severity': 'low',
                        'message': f'No updates in {days_stale} days',
                        'days': days_stale
                    })
        except Exception:
            pass
    
    # High story points not started
    points = task.get('story_points') or parse_story_points(task.get('name', ''))
    if points and points >= 8:
        status = (task.get('status') or '').lower()
        if status in ['to do', 'todo', 'open', 'planning']:
            score += 15
            flags.append({
                'type': 'high_complexity',
                'severity': 'medium',
                'message': f'High complexity ({points} points) not started'
            })
    
    # Determine risk level
    if score >= 50:
        level = 'HIGH'
    elif score >= 25:
        level = 'MEDIUM'
    else:
        level = 'LOW'
    
    return {
        'score': min(score, 100),
        'level': level,
        'flags': flags
    }


def analyze_tasks_for_project(tasks: List[dict]) -> dict:
    """Comprehensive task analysis for a project"""
    now = datetime.now(timezone.utc)
    
    # Initialize counters
    total_tasks = len(tasks)
    total_points = 0
    completed_points = 0
    completed_tasks = 0
    in_progress_tasks = 0
    blocked_tasks = 0
    overdue_tasks = 0
    unassigned_tasks = 0
    high_risk_tasks = 0
    medium_risk_tasks = 0
    
    task_analyses = []
    status_distribution = {}
    
    for task in tasks:
        # Parse story points
        points = task.get('story_points') or parse_story_points(task.get('name', '')) or 0
        total_points += points
        
        # Status tracking
        status = (task.get('status') or 'Unknown').lower()
        status_key = status.title()
        status_distribution[status_key] = status_distribution.get(status_key, 0) + 1
        
        if status in ['complete', 'done', 'closed', 'resolved']:
            completed_tasks += 1
            completed_points += points
        elif status in ['in progress', 'in review', 'review']:
            in_progress_tasks += 1
        
        # Calculate risk
        risk = calculate_task_risk(task)
        
        if risk['level'] == 'HIGH':
            high_risk_tasks += 1
        elif risk['level'] == 'MEDIUM':
            medium_risk_tasks += 1
        
        # Check specific flags
        for flag in risk['flags']:
            if flag['type'] == 'blocked':
                blocked_tasks += 1
            elif flag['type'] == 'overdue':
                overdue_tasks += 1
            elif flag['type'] == 'unassigned':
                unassigned_tasks += 1
        
        # Build task analysis
        assignees = task.get('assignees', [])
        assignee_names = [a.get('username') or a.get('email', 'Unknown') for a in assignees]
        
        task_analyses.append({
            'task_id': task.get('id'),
            'name': task.get('name', 'Unknown'),
            'status': status_key,
            'risk_score': risk['score'],
            'risk_level': risk['level'],
            'flags': risk['flags'],
            'assignees': assignee_names,
            'due_date': task.get('due_date'),
            'story_points': points,
            'list_name': task.get('list', {}).get('name') if isinstance(task.get('list'), dict) else task.get('list_name'),
            'url': task.get('url')
        })
    
    # Sort by risk score
    task_analyses.sort(key=lambda x: x['risk_score'], reverse=True)
    
    # Calculate velocity (if we have historical data, this would be more accurate)
    completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
    
    # Calculate overall risk score
    if total_tasks > 0:
        avg_risk = sum(t['risk_score'] for t in task_analyses) / total_tasks
    else:
        avg_risk = 0
    
    # Determine overall risk level
    if high_risk_tasks >= 3 or avg_risk >= 50:
        overall_level = 'HIGH'
    elif high_risk_tasks >= 1 or avg_risk >= 25:
        overall_level = 'MEDIUM'
    else:
        overall_level = 'LOW'
    
    return {
        'summary': {
            'total_tasks': total_tasks,
            'total_points': total_points,
            'completed_tasks': completed_tasks,
            'completed_points': completed_points,
            'remaining_points': total_points - completed_points,
            'in_progress_tasks': in_progress_tasks,
            'blocked_tasks': blocked_tasks,
            'overdue_tasks': overdue_tasks,
            'unassigned_tasks': unassigned_tasks,
            'high_risk_tasks': high_risk_tasks,
            'medium_risk_tasks': medium_risk_tasks,
            'completion_percentage': int(completion_rate * 100),
            'average_risk_score': int(avg_risk),
            'overall_risk_level': overall_level,
            'status_distribution': status_distribution
        },
        'tasks': task_analyses,
        'at_risk_tasks': [t for t in task_analyses if t['risk_level'] in ['HIGH', 'MEDIUM']][:10],
        'analyzed_at': now.isoformat()
    }


def calculate_burndown_data(tasks: List[dict], sprint_start: str, sprint_end: str) -> dict:
    """Calculate sprint burndown data"""
    try:
        start_dt = datetime.fromisoformat(sprint_start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(sprint_end.replace('Z', '+00:00'))
    except:
        start_dt = datetime.now(timezone.utc) - timedelta(days=7)
        end_dt = datetime.now(timezone.utc) + timedelta(days=7)
    
    now = datetime.now(timezone.utc)
    sprint_days = (end_dt - start_dt).days or 14
    days_elapsed = min((now - start_dt).days, sprint_days)
    
    # Calculate total and completed points
    total_points = sum(
        t.get('story_points') or parse_story_points(t.get('name', '')) or 0 
        for t in tasks
    )
    
    if total_points == 0:
        total_points = len(tasks)
    
    completed_points = sum(
        t.get('story_points') or parse_story_points(t.get('name', '')) or 0
        for t in tasks
        if (t.get('status') or '').lower() in ['complete', 'done', 'closed', 'resolved']
    )
    
    if total_points == len(tasks):
        completed_points = sum(
            1 for t in tasks 
            if (t.get('status') or '').lower() in ['complete', 'done', 'closed', 'resolved']
        )
    
    remaining = total_points - completed_points
    
    # Generate date labels
    dates = []
    ideal = []
    actual = []
    
    for i in range(sprint_days + 1):
        date = start_dt + timedelta(days=i)
        dates.append(date.strftime('%m/%d'))
        
        # Ideal burndown (linear)
        ideal_remaining = total_points - (total_points * i / sprint_days)
        ideal.append(round(ideal_remaining, 1))
        
        # Actual (we only know current state, so show flat then current)
        if i <= days_elapsed:
            # Simplified: linear progress to current
            if days_elapsed > 0:
                progress = completed_points * i / days_elapsed
                actual.append(round(total_points - progress, 1))
            else:
                actual.append(total_points)
        else:
            actual.append(None)  # Future dates
    
    # Calculate velocity
    if days_elapsed > 0:
        velocity = completed_points / days_elapsed
    else:
        velocity = 0
    
    return {
        'dates': dates,
        'ideal': ideal,
        'actual': actual,
        'total_points': total_points,
        'completed_points': completed_points,
        'remaining_points': remaining,
        'velocity': round(velocity, 2),
        'sprint_start': sprint_start,
        'sprint_end': sprint_end,
        'days_elapsed': days_elapsed,
        'days_remaining': sprint_days - days_elapsed
    }


def generate_standup_summary(tasks: List[dict], project_name: str) -> dict:
    """Generate AI-ready standup summary"""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    
    completed_yesterday = []
    in_progress_today = []
    blockers = []
    at_risk = []
    
    for task in tasks:
        status = (task.get('status') or '').lower()
        risk = calculate_task_risk(task)
        
        # Completed recently
        if status in ['complete', 'done', 'closed', 'resolved']:
            date_done = task.get('date_done') or task.get('date_updated')
            if date_done:
                try:
                    if isinstance(date_done, (int, float)):
                        done_dt = datetime.fromtimestamp(date_done/1000, tz=timezone.utc)
                    else:
                        done_dt = datetime.fromisoformat(str(date_done).replace('Z', '+00:00'))
                    
                    if done_dt >= yesterday:
                        completed_yesterday.append({
                            'name': task.get('name'),
                            'points': task.get('story_points') or parse_story_points(task.get('name', '')),
                            'assignee': task.get('assignees', [{}])[0].get('username', 'Unassigned') if task.get('assignees') else 'Unassigned'
                        })
                except:
                    pass
        
        # In progress
        elif status in ['in progress', 'in review', 'review']:
            in_progress_today.append({
                'name': task.get('name'),
                'points': task.get('story_points') or parse_story_points(task.get('name', '')),
                'assignee': task.get('assignees', [{}])[0].get('username', 'Unassigned') if task.get('assignees') else 'Unassigned',
                'risk_level': risk['level']
            })
        
        # Blockers
        if task.get('blocked') or any(f['type'] == 'blocked' for f in risk['flags']):
            blockers.append({
                'name': task.get('name'),
                'reason': 'Task marked as blocked'
            })
        
        # At risk (overdue or high risk)
        if risk['level'] == 'HIGH':
            at_risk.append({
                'name': task.get('name'),
                'risk_score': risk['score'],
                'issues': [f['message'] for f in risk['flags']]
            })
    
    # Calculate metrics
    analysis = analyze_tasks_for_project(tasks)
    summary = analysis['summary']
    
    # Generate talking points
    talking_points = []
    
    if completed_yesterday:
        talking_points.append(f"Completed {len(completed_yesterday)} task(s) since yesterday")
    
    if summary['overdue_tasks'] > 0:
        talking_points.append(f"⚠️ {summary['overdue_tasks']} task(s) are overdue - need to discuss timeline")
    
    if summary['blocked_tasks'] > 0:
        talking_points.append(f"🚫 {summary['blocked_tasks']} task(s) are blocked - need to resolve dependencies")
    
    if summary['unassigned_tasks'] > 0:
        talking_points.append(f"👤 {summary['unassigned_tasks']} task(s) need owners assigned")
    
    completion_pct = summary['completion_percentage']
    if completion_pct < 30:
        talking_points.append(f"📊 Sprint is {completion_pct}% complete - may need to re-prioritize")
    elif completion_pct > 70:
        talking_points.append(f"✅ Sprint is {completion_pct}% complete - on track for delivery")
    
    if not talking_points:
        talking_points.append("All tasks are on track. Continue current momentum.")
    
    return {
        'date': now.strftime('%Y-%m-%d'),
        'project_name': project_name,
        'completed_yesterday': completed_yesterday[:5],
        'in_progress_today': in_progress_today[:10],
        'blockers': blockers[:5],
        'at_risk_tasks': at_risk[:5],
        'key_metrics': {
            'total_tasks': summary['total_tasks'],
            'completed': summary['completed_tasks'],
            'in_progress': summary['in_progress_tasks'],
            'completion_pct': summary['completion_percentage'],
            'story_points_remaining': summary['remaining_points']
        },
        'talking_points': talking_points,
        'generated_at': now.isoformat()
    }


# ============== API ENDPOINT HANDLERS ==============
# Add these route handlers to your FastAPI router

"""
@api_router.get("/projects/{project_id}/task-analysis")
async def get_task_analysis(project_id: str, current_user: dict = Depends(get_current_user)):
    '''Get detailed task-level risk analysis for a project'''
    
    # Get latest sync data
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup"},
        sort=[("created_at", -1)]
    )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        raise HTTPException(status_code=404, detail="No task data found. Please sync ClickUp first.")
    
    tasks = sync["data"]["tasks"]
    analysis = analyze_tasks_for_project(tasks)
    
    return analysis


@api_router.get("/projects/{project_id}/burndown")
async def get_burndown_data(
    project_id: str, 
    sprint_start: str = None,
    sprint_end: str = None,
    current_user: dict = Depends(get_current_user)
):
    '''Get sprint burndown chart data'''
    
    # Get latest sync data
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup"},
        sort=[("created_at", -1)]
    )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        raise HTTPException(status_code=404, detail="No task data found")
    
    tasks = sync["data"]["tasks"]
    
    # Default sprint dates if not provided
    if not sprint_start:
        sprint_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    if not sprint_end:
        sprint_end = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    
    burndown = calculate_burndown_data(tasks, sprint_start, sprint_end)
    
    return burndown


@api_router.get("/projects/{project_id}/standup")
async def get_standup_summary(project_id: str, current_user: dict = Depends(get_current_user)):
    '''Generate AI standup summary for a project'''
    
    # Get project details
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get latest sync data
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup"},
        sort=[("created_at", -1)]
    )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        raise HTTPException(status_code=404, detail="No task data found")
    
    tasks = sync["data"]["tasks"]
    standup = generate_standup_summary(tasks, project.get("name", "Project"))
    
    # Store for history
    await db.standup_summaries.insert_one({
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "date": standup["date"],
        "summary": standup,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return standup


@api_router.get("/projects/{project_id}/trends")
async def get_risk_trends(
    project_id: str,
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    '''Get historical risk trend data'''
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    snapshots = await db.risk_snapshots.find(
        {
            "project_id": project_id,
            "created_at": {"$gte": cutoff.isoformat()}
        }
    ).sort("created_at", 1).to_list(100)
    
    trends = []
    for snap in snapshots:
        trends.append({
            "date": snap.get("snapshot_date", snap.get("created_at", ""))[:10],
            "overall_score": snap.get("overall_score", 0),
            "dimensions": snap.get("dimensions", {}),
            "task_count": snap.get("task_count", 0),
            "high_risk_count": snap.get("high_risk_count", 0)
        })
    
    return {"trends": trends, "period_days": days}


@api_router.post("/projects/{project_id}/snapshot")
async def create_risk_snapshot(project_id: str, current_user: dict = Depends(get_current_user)):
    '''Create a point-in-time risk snapshot for trend tracking'''
    
    # Get latest analysis
    assessment = await db.risk_assessments.find_one(
        {"project_id": project_id},
        sort=[("created_at", -1)]
    )
    
    # Get task data
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup"},
        sort=[("created_at", -1)]
    )
    
    tasks = sync.get("data", {}).get("tasks", []) if sync else []
    analysis = analyze_tasks_for_project(tasks) if tasks else {"summary": {}}
    
    snapshot = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "overall_score": assessment.get("risk_score", 0) if assessment else analysis["summary"].get("average_risk_score", 0),
        "dimensions": assessment.get("risk_dimensions", {}) if assessment else {},
        "task_count": analysis["summary"].get("total_tasks", 0),
        "high_risk_count": analysis["summary"].get("high_risk_tasks", 0),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.risk_snapshots.insert_one(snapshot)
    
    return {"message": "Snapshot created", "snapshot_id": snapshot["id"]}
"""

# Export for use in server.py
__all__ = [
    'calculate_task_risk',
    'analyze_tasks_for_project', 
    'calculate_burndown_data',
    'generate_standup_summary',
    'parse_story_points'
]
