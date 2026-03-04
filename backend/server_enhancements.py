# server_enhancements.py
# Complete backend enhancements for Delivery Risk Radar v2.0
# Copy these additions to server.py

"""
=== IMPORTS TO ADD AT TOP OF server.py ===

import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import asyncio
"""


# ============== NEW MODELS ==============

class NotificationConfigCreate(BaseModel):
    slack_enabled: bool = False
    slack_webhook: Optional[str] = None
    slack_channel: str = "#risk-alerts"
    email_enabled: bool = False
    email_recipients: Optional[str] = None
    digest_frequency: str = "daily"  # daily, weekly, realtime
    alert_threshold: int = 50
    alert_on_high_risk: bool = True
    alert_on_overdue: bool = True
    alert_on_blocked: bool = True


class SprintConfig(BaseModel):
    project_id: str
    sprint_name: Optional[str] = None
    start_date: str
    end_date: str
    list_ids: Optional[List[str]] = None


# ============== HELPER FUNCTIONS ==============

def parse_story_points_from_name(task_name: str) -> Optional[int]:
    """Extract story points from task name like [SP:5] or [5]"""
    patterns = [
        r'\[SP:(\d+)\]',
        r'\[(\d+)\s*(?:pts?|points?)\]',
        r'\((\d+)\s*(?:pts?|points?)\)',
    ]
    for pattern in patterns:
        match = re.search(pattern, task_name, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def calculate_task_risk_score(task: dict) -> dict:
    """Calculate individual task risk score with detailed flags"""
    score = 0
    flags = []
    now = datetime.now(timezone.utc)
    
    status = (task.get('status') or '').lower()
    is_completed = status in ['complete', 'done', 'closed', 'resolved', 'completed']
    
    # Check overdue
    due_date = task.get('due_date')
    if due_date and not is_completed:
        try:
            if isinstance(due_date, str):
                due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            elif isinstance(due_date, (int, float)):
                due_dt = datetime.fromtimestamp(due_date/1000, tz=timezone.utc)
            else:
                due_dt = None
            
            if due_dt:
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
        except Exception as e:
            logger.warning(f"Error parsing due date: {e}")
    elif not due_date and not is_completed and status not in ['backlog', 'icebox']:
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
    
    # Check dependencies (blockers)
    dependencies = task.get('dependencies', [])
    if dependencies and len(dependencies) > 0:
        blocking_deps = [d for d in dependencies if d.get('type') == 'waiting_on']
        if blocking_deps:
            score += 10
            flags.append({
                'type': 'has_dependencies',
                'severity': 'medium',
                'message': f'Waiting on {len(blocking_deps)} task(s)'
            })
    
    # Check unassigned
    assignees = task.get('assignees', [])
    if not assignees and not is_completed:
        score += 15
        flags.append({
            'type': 'unassigned',
            'severity': 'medium',
            'message': 'No assignee'
        })
    
    # Check stale (no updates in 7+ days for active tasks)
    if not is_completed:
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
            except Exception as e:
                logger.warning(f"Error parsing updated date: {e}")
    
    # High story points not started
    points = task.get('story_points') or parse_story_points_from_name(task.get('name', ''))
    if points and points >= 8 and not is_completed:
        if status in ['to do', 'todo', 'open', 'planning', 'backlog']:
            score += 15
            flags.append({
                'type': 'high_complexity',
                'severity': 'medium',
                'message': f'High complexity ({points} pts) not started'
            })
    
    # Scope creep indicator - task description changed multiple times (if available)
    if task.get('description_change_count', 0) > 3:
        score += 10
        flags.append({
            'type': 'scope_creep',
            'severity': 'low',
            'message': 'Frequent description changes'
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


def analyze_all_tasks(tasks: List[dict]) -> dict:
    """Comprehensive analysis of all tasks"""
    now = datetime.now(timezone.utc)
    
    total_tasks = len(tasks)
    total_points = 0
    completed_points = 0
    completed_tasks = 0
    in_progress_tasks = 0
    blocked_tasks = 0
    overdue_tasks = 0
    unassigned_tasks = 0
    high_risk = 0
    medium_risk = 0
    
    task_analyses = []
    status_distribution = {}
    assignee_workload = {}
    
    for task in tasks:
        # Parse story points
        points = task.get('story_points') or parse_story_points_from_name(task.get('name', '')) or 0
        total_points += points
        
        # Status tracking
        status = (task.get('status') or 'Unknown')
        status_key = status.title()
        status_distribution[status_key] = status_distribution.get(status_key, 0) + 1
        
        if status.lower() in ['complete', 'done', 'closed', 'resolved', 'completed']:
            completed_tasks += 1
            completed_points += points
        elif status.lower() in ['in progress', 'in review', 'review', 'doing']:
            in_progress_tasks += 1
        
        # Assignee tracking
        assignees = task.get('assignees', [])
        for assignee in assignees:
            name = assignee.get('username') or assignee.get('email', 'Unknown')
            if name not in assignee_workload:
                assignee_workload[name] = {'total': 0, 'in_progress': 0, 'points': 0}
            assignee_workload[name]['total'] += 1
            assignee_workload[name]['points'] += points
            if status.lower() in ['in progress', 'in review', 'review', 'doing']:
                assignee_workload[name]['in_progress'] += 1
        
        # Calculate risk
        risk = calculate_task_risk_score(task)
        
        if risk['level'] == 'HIGH':
            high_risk += 1
        elif risk['level'] == 'MEDIUM':
            medium_risk += 1
        
        # Check specific flags for counters
        for flag in risk['flags']:
            if flag['type'] == 'blocked':
                blocked_tasks += 1
            elif flag['type'] == 'overdue':
                overdue_tasks += 1
            elif flag['type'] == 'unassigned':
                unassigned_tasks += 1
        
        # Build task analysis
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
            'url': task.get('url'),
            'priority': task.get('priority', {}).get('priority') if isinstance(task.get('priority'), dict) else task.get('priority'),
            'tags': [t.get('name') for t in task.get('tags', [])] if task.get('tags') else [],
            'created_at': task.get('date_created'),
            'updated_at': task.get('date_updated')
        })
    
    # Sort by risk score
    task_analyses.sort(key=lambda x: x['risk_score'], reverse=True)
    
    # Calculate metrics
    completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
    avg_risk = sum(t['risk_score'] for t in task_analyses) / total_tasks if total_tasks > 0 else 0
    
    # Determine overall risk level
    if high_risk >= 3 or avg_risk >= 50 or overdue_tasks >= 3:
        overall_level = 'HIGH'
    elif high_risk >= 1 or avg_risk >= 25 or overdue_tasks >= 1:
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
            'high_risk_tasks': high_risk,
            'medium_risk_tasks': medium_risk,
            'low_risk_tasks': total_tasks - high_risk - medium_risk,
            'completion_percentage': int(completion_rate * 100),
            'average_risk_score': int(avg_risk),
            'overall_risk_level': overall_level,
            'status_distribution': status_distribution,
            'assignee_workload': assignee_workload
        },
        'tasks': task_analyses,
        'at_risk_tasks': [t for t in task_analyses if t['risk_level'] in ['HIGH', 'MEDIUM']][:15],
        'analyzed_at': now.isoformat()
    }


def calculate_burndown(tasks: List[dict], sprint_start: str, sprint_end: str) -> dict:
    """Calculate sprint burndown data"""
    try:
        start_dt = datetime.fromisoformat(sprint_start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(sprint_end.replace('Z', '+00:00'))
    except:
        start_dt = datetime.now(timezone.utc) - timedelta(days=7)
        end_dt = datetime.now(timezone.utc) + timedelta(days=7)
    
    now = datetime.now(timezone.utc)
    sprint_days = (end_dt - start_dt).days or 14
    days_elapsed = min(max((now - start_dt).days, 0), sprint_days)
    
    # Calculate points
    total_points = sum(
        t.get('story_points') or parse_story_points_from_name(t.get('name', '')) or 0 
        for t in tasks
    )
    
    # If no story points, use task count
    use_task_count = total_points == 0
    if use_task_count:
        total_points = len(tasks)
    
    completed_points = 0
    for t in tasks:
        if (t.get('status') or '').lower() in ['complete', 'done', 'closed', 'resolved', 'completed']:
            if use_task_count:
                completed_points += 1
            else:
                completed_points += t.get('story_points') or parse_story_points_from_name(t.get('name', '')) or 0
    
    remaining = total_points - completed_points
    
    # Generate chart data
    dates = []
    ideal = []
    actual = []
    
    for i in range(sprint_days + 1):
        date = start_dt + timedelta(days=i)
        dates.append(date.strftime('%m/%d'))
        
        # Ideal burndown (linear)
        ideal_remaining = total_points * (1 - i / sprint_days)
        ideal.append(round(ideal_remaining, 1))
        
        # Actual progress
        if i <= days_elapsed:
            if days_elapsed > 0:
                progress = completed_points * i / days_elapsed
                actual.append(round(total_points - progress, 1))
            else:
                actual.append(float(total_points))
        else:
            actual.append(None)
    
    # Velocity
    velocity = completed_points / days_elapsed if days_elapsed > 0 else 0
    
    # Projected completion
    if velocity > 0:
        days_to_complete = remaining / velocity
        projected_end = now + timedelta(days=days_to_complete)
        on_track = projected_end <= end_dt
    else:
        projected_end = None
        on_track = completed_points >= total_points
    
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
        'days_remaining': sprint_days - days_elapsed,
        'on_track': on_track,
        'projected_end': projected_end.isoformat() if projected_end else None,
        'unit': 'tasks' if use_task_count else 'points'
    }


def generate_standup(tasks: List[dict], project_name: str) -> dict:
    """Generate comprehensive standup summary"""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    
    completed_yesterday = []
    in_progress_today = []
    blockers = []
    at_risk = []
    coming_due = []
    
    for task in tasks:
        status = (task.get('status') or '').lower()
        risk = calculate_task_risk_score(task)
        assignees = task.get('assignees', [])
        assignee = assignees[0].get('username', 'Unassigned') if assignees else 'Unassigned'
        points = task.get('story_points') or parse_story_points_from_name(task.get('name', ''))
        
        task_info = {
            'id': task.get('id'),
            'name': task.get('name'),
            'points': points,
            'assignee': assignee,
            'status': status.title(),
            'url': task.get('url')
        }
        
        # Completed recently
        if status in ['complete', 'done', 'closed', 'resolved', 'completed']:
            date_done = task.get('date_done') or task.get('date_updated')
            if date_done:
                try:
                    if isinstance(date_done, (int, float)):
                        done_dt = datetime.fromtimestamp(date_done/1000, tz=timezone.utc)
                    else:
                        done_dt = datetime.fromisoformat(str(date_done).replace('Z', '+00:00'))
                    
                    if done_dt >= yesterday:
                        completed_yesterday.append(task_info)
                except:
                    pass
        
        # In progress
        elif status in ['in progress', 'in review', 'review', 'doing']:
            task_info['risk_level'] = risk['level']
            task_info['risk_flags'] = [f['message'] for f in risk['flags']]
            in_progress_today.append(task_info)
        
        # Blockers
        if task.get('blocked') or any(f['type'] == 'blocked' for f in risk['flags']):
            blockers.append({
                **task_info,
                'reason': 'Task marked as blocked'
            })
        
        # At risk
        if risk['level'] == 'HIGH':
            at_risk.append({
                **task_info,
                'risk_score': risk['score'],
                'issues': [f['message'] for f in risk['flags']]
            })
        
        # Coming due in next 2 days
        due_date = task.get('due_date')
        if due_date and status not in ['complete', 'done', 'closed', 'resolved', 'completed']:
            try:
                if isinstance(due_date, str):
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                elif isinstance(due_date, (int, float)):
                    due_dt = datetime.fromtimestamp(due_date/1000, tz=timezone.utc)
                else:
                    due_dt = None
                
                if due_dt and now <= due_dt <= now + timedelta(days=2):
                    coming_due.append({
                        **task_info,
                        'due_date': due_dt.strftime('%m/%d'),
                        'days_until_due': (due_dt - now).days
                    })
            except:
                pass
    
    # Calculate metrics
    analysis = analyze_all_tasks(tasks)
    summary = analysis['summary']
    
    # Generate talking points
    talking_points = []
    
    if completed_yesterday:
        total_pts = sum(t.get('points') or 0 for t in completed_yesterday)
        talking_points.append(f"✅ Completed {len(completed_yesterday)} task(s) ({total_pts} pts) since yesterday")
    
    if summary['overdue_tasks'] > 0:
        talking_points.append(f"⚠️ {summary['overdue_tasks']} task(s) are overdue - need to discuss timeline")
    
    if summary['blocked_tasks'] > 0:
        talking_points.append(f"🚫 {summary['blocked_tasks']} task(s) are blocked - need to resolve dependencies")
    
    if summary['unassigned_tasks'] > 0:
        talking_points.append(f"👤 {summary['unassigned_tasks']} task(s) need owners assigned")
    
    if coming_due:
        talking_points.append(f"📅 {len(coming_due)} task(s) due in next 2 days")
    
    completion_pct = summary['completion_percentage']
    if completion_pct < 30:
        talking_points.append(f"📊 Sprint is {completion_pct}% complete - may need to re-prioritize")
    elif completion_pct > 70:
        talking_points.append(f"🎯 Sprint is {completion_pct}% complete - on track for delivery")
    
    # Team workload summary
    workload = summary.get('assignee_workload', {})
    overloaded = [name for name, data in workload.items() if data.get('in_progress', 0) > 5]
    if overloaded:
        talking_points.append(f"⚡ {', '.join(overloaded[:3])} may be overloaded (5+ active tasks)")
    
    if not talking_points:
        talking_points.append("✓ All tasks are on track. Continue current momentum.")
    
    # Generate recommendations
    recommendations = []
    if summary['overdue_tasks'] > 0:
        recommendations.append("Schedule sync with team to address overdue items")
    if summary['blocked_tasks'] > 0:
        recommendations.append("Identify blocker owners and set resolution deadlines")
    if summary['unassigned_tasks'] > 0:
        recommendations.append("Assign owners during standup to maintain accountability")
    if summary['high_risk_tasks'] > 2:
        recommendations.append("Consider escalating high-risk items to stakeholders")
    
    return {
        'date': now.strftime('%Y-%m-%d'),
        'project_name': project_name,
        'completed_yesterday': completed_yesterday[:10],
        'in_progress_today': sorted(in_progress_today, key=lambda x: x.get('risk_level', '') == 'HIGH', reverse=True)[:15],
        'blockers': blockers[:10],
        'at_risk_tasks': at_risk[:10],
        'coming_due': coming_due[:10],
        'key_metrics': {
            'total_tasks': summary['total_tasks'],
            'completed': summary['completed_tasks'],
            'in_progress': summary['in_progress_tasks'],
            'completion_pct': summary['completion_percentage'],
            'story_points_remaining': summary['remaining_points'],
            'high_risk_count': summary['high_risk_tasks'],
            'blocked_count': summary['blocked_tasks'],
            'overdue_count': summary['overdue_tasks']
        },
        'talking_points': talking_points,
        'recommendations': recommendations,
        'team_workload': workload,
        'generated_at': now.isoformat()
    }


async def send_slack_notification(webhook_url: str, message: dict) -> bool:
    """Send notification to Slack"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=message, timeout=10)
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")
        return False


async def send_email_notification(recipients: List[str], subject: str, body: str) -> bool:
    """Send email notification"""
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    
    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not configured")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = ', '.join(recipients)
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipients, msg.as_string())
        
        return True
    except Exception as e:
        logger.error(f"Email notification failed: {e}")
        return False


def build_slack_risk_alert(project_name: str, analysis: dict) -> dict:
    """Build Slack message for risk alert"""
    summary = analysis.get('summary', {})
    at_risk = analysis.get('at_risk_tasks', [])[:5]
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🚨 Risk Alert: {project_name}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Risk Level:*\n{summary.get('overall_risk_level', 'N/A')}"},
                {"type": "mrkdwn", "text": f"*Risk Score:*\n{summary.get('average_risk_score', 0)}%"},
                {"type": "mrkdwn", "text": f"*High Risk Tasks:*\n{summary.get('high_risk_tasks', 0)}"},
                {"type": "mrkdwn", "text": f"*Overdue:*\n{summary.get('overdue_tasks', 0)}"}
            ]
        },
        {"type": "divider"}
    ]
    
    if at_risk:
        task_list = "\n".join([f"• {t['name'][:50]} ({t['risk_level']})" for t in at_risk])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Top At-Risk Tasks:*\n{task_list}"
            }
        })
    
    return {"blocks": blocks}


# ============== API ENDPOINTS ==============

# --- Task Analysis ---
@api_router.get("/projects/{project_id}/task-analysis")
async def get_task_analysis(project_id: str, current_user: dict = Depends(get_current_user)):
    """Get detailed task-level risk analysis for a project"""
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup"},
        sort=[("created_at", -1)]
    )
    
    if not sync:
        # Try Jira
        sync = await db.data_syncs.find_one(
            {"project_id": project_id, "source": "jira"},
            sort=[("created_at", -1)]
        )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        raise HTTPException(status_code=404, detail="No task data found. Please sync first.")
    
    tasks = sync["data"]["tasks"]
    analysis = analyze_all_tasks(tasks)
    
    return analysis


# --- Burndown Chart ---
@api_router.get("/projects/{project_id}/burndown")
async def get_burndown_data(
    project_id: str, 
    sprint_start: str = None,
    sprint_end: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Get sprint burndown chart data"""
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup"},
        sort=[("created_at", -1)]
    )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        raise HTTPException(status_code=404, detail="No task data found")
    
    tasks = sync["data"]["tasks"]
    
    # Try to get sprint config
    sprint = await db.sprint_configs.find_one({"project_id": project_id}, sort=[("created_at", -1)])
    
    if not sprint_start:
        sprint_start = sprint.get('start_date') if sprint else (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    if not sprint_end:
        sprint_end = sprint.get('end_date') if sprint else (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    
    burndown = calculate_burndown(tasks, sprint_start, sprint_end)
    return burndown


# --- Standup Summary ---
@api_router.get("/projects/{project_id}/standup")
async def get_standup_summary(project_id: str, current_user: dict = Depends(get_current_user)):
    """Generate AI standup summary for a project"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup"},
        sort=[("created_at", -1)]
    )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        raise HTTPException(status_code=404, detail="No task data found")
    
    tasks = sync["data"]["tasks"]
    standup = generate_standup(tasks, project.get("name", "Project"))
    
    # Store for history
    await db.standup_summaries.update_one(
        {"project_id": project_id, "date": standup["date"]},
        {"$set": {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "date": standup["date"],
            "summary": standup,
            "created_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return standup


# --- Historical Trends ---
@api_router.get("/projects/{project_id}/trends")
async def get_risk_trends(
    project_id: str,
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get historical risk trend data"""
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
            "high_risk_count": snap.get("high_risk_count", 0),
            "overdue_count": snap.get("overdue_count", 0),
            "blocked_count": snap.get("blocked_count", 0)
        })
    
    return {"trends": trends, "period_days": days}


# --- Create Risk Snapshot ---
@api_router.post("/projects/{project_id}/snapshot")
async def create_risk_snapshot(project_id: str, current_user: dict = Depends(get_current_user)):
    """Create a point-in-time risk snapshot for trend tracking"""
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
    analysis = analyze_all_tasks(tasks) if tasks else {"summary": {}}
    summary = analysis.get("summary", {})
    
    snapshot = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "overall_score": assessment.get("risk_score", 0) if assessment else summary.get("average_risk_score", 0),
        "dimensions": assessment.get("risk_dimensions", {}) if assessment else {},
        "task_count": summary.get("total_tasks", 0),
        "high_risk_count": summary.get("high_risk_tasks", 0),
        "overdue_count": summary.get("overdue_tasks", 0),
        "blocked_count": summary.get("blocked_tasks", 0),
        "completion_pct": summary.get("completion_percentage", 0),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.risk_snapshots.insert_one(snapshot)
    
    return {"message": "Snapshot created", "snapshot_id": snapshot["id"]}


# --- Sprint Configuration ---
@api_router.post("/projects/{project_id}/sprint-config")
async def save_sprint_config(project_id: str, config: SprintConfig, current_user: dict = Depends(get_current_user)):
    """Save sprint configuration for a project"""
    sprint_doc = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "sprint_name": config.sprint_name,
        "start_date": config.start_date,
        "end_date": config.end_date,
        "list_ids": config.list_ids,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sprint_configs.insert_one(sprint_doc)
    return {"message": "Sprint configuration saved", "id": sprint_doc["id"]}


@api_router.get("/projects/{project_id}/sprint-config")
async def get_sprint_config(project_id: str, current_user: dict = Depends(get_current_user)):
    """Get current sprint configuration"""
    sprint = await db.sprint_configs.find_one(
        {"project_id": project_id},
        sort=[("created_at", -1)]
    )
    
    if sprint:
        sprint.pop("_id", None)
    
    return sprint or {}


# --- Notification Settings ---
@api_router.post("/settings/notifications")
async def save_notification_config(config: NotificationConfigCreate, current_user: dict = Depends(get_current_user)):
    """Save notification configuration"""
    config_doc = {
        "user_id": current_user["id"],
        **config.dict(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.notification_configs.update_one(
        {"user_id": current_user["id"]},
        {"$set": config_doc},
        upsert=True
    )
    
    return {"message": "Notification settings saved"}


@api_router.get("/settings/notifications")
async def get_notification_config(current_user: dict = Depends(get_current_user)):
    """Get notification configuration"""
    config = await db.notification_configs.find_one(
        {"user_id": current_user["id"]},
        {"_id": 0, "user_id": 0}
    )
    return config or {}


# --- Test Notifications ---
@api_router.post("/notifications/test-slack")
async def test_slack_notification(webhook: dict, current_user: dict = Depends(get_current_user)):
    """Send test Slack notification"""
    webhook_url = webhook.get("webhook")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Webhook URL required")
    
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🧪 Test Alert from Risk Radar",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"This is a test notification from Delivery Risk Radar.\n\n*Sent by:* {current_user.get('name', 'Unknown')}\n*Time:* {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                }
            }
        ]
    }
    
    success = await send_slack_notification(webhook_url, message)
    
    if success:
        return {"message": "Test notification sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send notification")


@api_router.post("/notifications/test-email")
async def test_email_notification(data: dict, current_user: dict = Depends(get_current_user)):
    """Send test email notification"""
    recipients = data.get("recipients", "")
    if not recipients:
        raise HTTPException(status_code=400, detail="Recipients required")
    
    recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]
    
    subject = "🧪 Test Alert from Risk Radar"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #1E3A5F;">Test Alert from Delivery Risk Radar</h2>
        <p>This is a test notification to verify your email configuration.</p>
        <p><strong>Sent by:</strong> {current_user.get('name', 'Unknown')}</p>
        <p><strong>Time:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            You are receiving this because you configured email notifications in Risk Radar.
        </p>
    </body>
    </html>
    """
    
    success = await send_email_notification(recipient_list, subject, body)
    
    if success:
        return {"message": "Test email sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email. Check SMTP configuration.")


# --- Send Alert (Background Task) ---
async def check_and_send_alerts(project_id: str, analysis: dict):
    """Check thresholds and send alerts if needed"""
    # Get all users with notification configs for this project
    configs = await db.notification_configs.find({}).to_list(100)
    
    project = await db.projects.find_one({"id": project_id})
    project_name = project.get("name", "Unknown Project") if project else "Unknown Project"
    
    summary = analysis.get("summary", {})
    
    for config in configs:
        should_alert = False
        
        # Check threshold
        if summary.get("average_risk_score", 0) >= config.get("alert_threshold", 50):
            should_alert = True
        
        # Check specific triggers
        if config.get("alert_on_high_risk") and summary.get("high_risk_tasks", 0) > 0:
            should_alert = True
        
        if config.get("alert_on_overdue") and summary.get("overdue_tasks", 0) > 0:
            should_alert = True
        
        if config.get("alert_on_blocked") and summary.get("blocked_tasks", 0) > 0:
            should_alert = True
        
        if should_alert:
            # Slack
            if config.get("slack_enabled") and config.get("slack_webhook"):
                message = build_slack_risk_alert(project_name, analysis)
                await send_slack_notification(config["slack_webhook"], message)
            
            # Email (for realtime only)
            if config.get("email_enabled") and config.get("digest_frequency") == "realtime":
                recipients = [r.strip() for r in config.get("email_recipients", "").split(",") if r.strip()]
                if recipients:
                    subject = f"🚨 Risk Alert: {project_name}"
                    body = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; padding: 20px;">
                        <h2 style="color: #DC2626;">Risk Alert: {project_name}</h2>
                        <p><strong>Risk Level:</strong> {summary.get('overall_risk_level', 'N/A')}</p>
                        <p><strong>Risk Score:</strong> {summary.get('average_risk_score', 0)}%</p>
                        <p><strong>High Risk Tasks:</strong> {summary.get('high_risk_tasks', 0)}</p>
                        <p><strong>Overdue Tasks:</strong> {summary.get('overdue_tasks', 0)}</p>
                        <p><strong>Blocked Tasks:</strong> {summary.get('blocked_tasks', 0)}</p>
                        <hr>
                        <p><a href="#">View in Risk Radar</a></p>
                    </body>
                    </html>
                    """
                    await send_email_notification(recipients, subject, body)


# --- Dependencies Visualization ---
@api_router.get("/projects/{project_id}/dependencies")
async def get_task_dependencies(project_id: str, current_user: dict = Depends(get_current_user)):
    """Get task dependency graph data"""
    sync = await db.data_syncs.find_one(
        {"project_id": project_id, "source": "clickup"},
        sort=[("created_at", -1)]
    )
    
    if not sync or not sync.get("data", {}).get("tasks"):
        raise HTTPException(status_code=404, detail="No task data found")
    
    tasks = sync["data"]["tasks"]
    
    nodes = []
    edges = []
    blocked_chains = []
    
    task_map = {t.get('id'): t for t in tasks}
    
    for task in tasks:
        task_id = task.get('id')
        status = (task.get('status') or '').lower()
        risk = calculate_task_risk_score(task)
        
        nodes.append({
            'id': task_id,
            'name': task.get('name', 'Unknown')[:40],
            'status': status,
            'risk_level': risk['level'],
            'risk_score': risk['score'],
            'assignee': task.get('assignees', [{}])[0].get('username', 'Unassigned') if task.get('assignees') else 'Unassigned',
            'blocked': task.get('blocked', False)
        })
        
        # Process dependencies
        dependencies = task.get('dependencies', [])
        for dep in dependencies:
            dep_id = dep.get('task_id')
            dep_type = dep.get('type', 'unknown')
            
            if dep_id and dep_id in task_map:
                edges.append({
                    'from': dep_id,
                    'to': task_id,
                    'type': dep_type
                })
                
                # Check if this creates a blocked chain
                if task.get('blocked') or dep_type == 'waiting_on':
                    dep_task = task_map.get(dep_id)
                    if dep_task:
                        dep_status = (dep_task.get('status') or '').lower()
                        if dep_status not in ['complete', 'done', 'closed']:
                            blocked_chains.append({
                                'blocked_task': task.get('name'),
                                'blocking_task': dep_task.get('name'),
                                'blocking_status': dep_status
                            })
    
    return {
        'nodes': nodes,
        'edges': edges,
        'blocked_chains': blocked_chains[:20],
        'total_dependencies': len(edges),
        'blocked_count': len([n for n in nodes if n['blocked']])
    }


# --- Standup History ---
@api_router.get("/projects/{project_id}/standup-history")
async def get_standup_history(
    project_id: str, 
    days: int = 14,
    current_user: dict = Depends(get_current_user)
):
    """Get standup summary history"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    
    standups = await db.standup_summaries.find(
        {"project_id": project_id, "date": {"$gte": cutoff}},
        {"_id": 0}
    ).sort("date", -1).to_list(days)
    
    return {"standups": standups}
