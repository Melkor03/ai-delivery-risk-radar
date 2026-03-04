#!/usr/bin/env python3
"""
Delivery Risk Radar - Standalone Test Script
Tests risk detection logic against ClickUp data via API

This script bypasses the need for MongoDB/FastAPI and directly tests
the risk analysis algorithms against your ClickUp sandbox.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum

# Risk levels
class RiskLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass
class RiskSignal:
    """Individual risk signal detected"""
    dimension: str
    severity: str  # HIGH, MEDIUM, LOW
    message: str
    evidence: Dict[str, Any]

@dataclass 
class RiskAnalysis:
    """Complete risk analysis for a sprint/project"""
    overall_score: int  # 0-100
    risk_level: RiskLevel
    dimensions: Dict[str, int]  # Score per dimension 0-100
    signals: List[RiskSignal]
    recommendations: List[str]
    narrative: str

def analyze_sprint_risks(tasks: List[Dict], sprint_name: str, sprint_end: Optional[datetime] = None) -> RiskAnalysis:
    """
    Core risk analysis engine
    
    Analyzes tasks for 6 risk dimensions:
    1. Scope Creep - Uncontrolled scope changes
    2. Dependency Failure - Blocked/waiting tasks
    3. False Reporting - Status vs reality gaps  
    4. Quality Collapse - Bug patterns
    5. Team Burnout - Workload issues
    6. Delivery Risk - Schedule slippage
    """
    
    signals: List[RiskSignal] = []
    dimensions = {
        "scope_creep": 0,
        "dependency_failure": 0,
        "false_reporting": 0,
        "quality_collapse": 0,
        "team_burnout": 0,
        "delivery_risk": 0
    }
    
    now = datetime.now(timezone.utc)
    
    # Task counters
    total_tasks = len(tasks)
    if total_tasks == 0:
        return RiskAnalysis(
            overall_score=0,
            risk_level=RiskLevel.LOW,
            dimensions=dimensions,
            signals=[],
            recommendations=["No tasks found - add tasks to analyze"],
            narrative="No tasks available for analysis."
        )
    
    # Status analysis
    status_counts = {}
    for task in tasks:
        status = task.get("status", "Unknown").lower()
        status_counts[status] = status_counts.get(status, 0) + 1
    
    todo_count = status_counts.get("to do", 0) + status_counts.get("planning", 0)
    in_progress_count = status_counts.get("in progress", 0)
    blocked_count = status_counts.get("blocked", 0) + status_counts.get("at risk", 0) + status_counts.get("on hold", 0)
    done_count = status_counts.get("complete", 0) + status_counts.get("done", 0) + status_counts.get("closed", 0)
    
    # Priority analysis
    urgent_count = sum(1 for t in tasks if t.get("priority", "").lower() == "urgent")
    high_priority_count = sum(1 for t in tasks if t.get("priority", "").lower() == "high")
    
    # Due date analysis
    overdue_tasks = []
    no_due_date_count = 0
    for task in tasks:
        due = task.get("due_date")
        status = task.get("status", "").lower()
        if due and status not in ["complete", "done", "closed"]:
            try:
                if isinstance(due, str):
                    due_dt = datetime.fromisoformat(due.replace('Z', '+00:00'))
                else:
                    due_dt = datetime.fromtimestamp(int(due) / 1000, tz=timezone.utc)
                if due_dt < now:
                    overdue_tasks.append(task)
            except (ValueError, TypeError):
                pass
        elif not due and status not in ["complete", "done", "closed"]:
            no_due_date_count += 1
    
    # Story points analysis
    total_points = 0
    completed_points = 0
    unassigned_tasks = []
    
    for task in tasks:
        # Parse story points from task name [SP:X] format
        name = task.get("summary", "") or task.get("name", "")
        points = 0
        if "[SP:" in name:
            try:
                sp_str = name.split("[SP:")[1].split("]")[0]
                points = int(sp_str)
            except (IndexError, ValueError):
                pass
        
        total_points += points
        status = task.get("status", "").lower()
        if status in ["complete", "done", "closed"]:
            completed_points += points
        
        if not task.get("assignee") and not task.get("assignees"):
            unassigned_tasks.append(task)
    
    completion_rate = (completed_points / total_points * 100) if total_points > 0 else 0
    
    # ============== RISK DIMENSION SCORING ==============
    
    # 1. SCOPE CREEP (based on planning state tasks mid-sprint)
    planning_ratio = todo_count / total_tasks if total_tasks > 0 else 0
    if planning_ratio > 0.6:
        dimensions["scope_creep"] = 80
        signals.append(RiskSignal(
            dimension="Scope Creep",
            severity="HIGH",
            message=f"{todo_count} of {total_tasks} tasks still in 'To Do' or 'Planning' state",
            evidence={"todo_count": todo_count, "total": total_tasks, "ratio": planning_ratio}
        ))
    elif planning_ratio > 0.4:
        dimensions["scope_creep"] = 50
        signals.append(RiskSignal(
            dimension="Scope Creep",
            severity="MEDIUM",
            message=f"{int(planning_ratio * 100)}% of tasks not yet started",
            evidence={"todo_count": todo_count, "total": total_tasks}
        ))
    
    # 2. DEPENDENCY FAILURE (blocked tasks)
    if blocked_count > 0:
        block_ratio = blocked_count / total_tasks
        if block_ratio > 0.2:
            dimensions["dependency_failure"] = 90
            signals.append(RiskSignal(
                dimension="Dependency Failure",
                severity="HIGH",
                message=f"{blocked_count} tasks are blocked/at risk/on hold",
                evidence={"blocked_count": blocked_count, "status_counts": status_counts}
            ))
        else:
            dimensions["dependency_failure"] = 50
            signals.append(RiskSignal(
                dimension="Dependency Failure",
                severity="MEDIUM",
                message=f"{blocked_count} blocked task(s) detected",
                evidence={"blocked_count": blocked_count}
            ))
    
    # 3. DELIVERY RISK (overdue + completion rate)
    if len(overdue_tasks) > 0:
        overdue_ratio = len(overdue_tasks) / total_tasks
        if overdue_ratio > 0.3 or len(overdue_tasks) >= 3:
            dimensions["delivery_risk"] = 90
            signals.append(RiskSignal(
                dimension="Delivery Risk",
                severity="HIGH",
                message=f"{len(overdue_tasks)} tasks are OVERDUE",
                evidence={"overdue_tasks": [t.get("summary", t.get("name")) for t in overdue_tasks]}
            ))
        else:
            dimensions["delivery_risk"] = 60
            signals.append(RiskSignal(
                dimension="Delivery Risk",
                severity="MEDIUM",
                message=f"{len(overdue_tasks)} overdue task(s)",
                evidence={"overdue_count": len(overdue_tasks)}
            ))
    
    # Low completion rate
    if total_points > 0 and completion_rate < 20:
        dimensions["delivery_risk"] = max(dimensions["delivery_risk"], 70)
        signals.append(RiskSignal(
            dimension="Delivery Risk",
            severity="HIGH",
            message=f"Only {completion_rate:.0f}% of story points completed ({completed_points}/{total_points})",
            evidence={"completed": completed_points, "total": total_points}
        ))
    
    # 4. TEAM BURNOUT (unassigned tasks, urgent pile-up)
    if len(unassigned_tasks) > 0:
        unassigned_ratio = len(unassigned_tasks) / total_tasks
        if unassigned_ratio > 0.3:
            dimensions["team_burnout"] = 60
            signals.append(RiskSignal(
                dimension="Team Burnout",
                severity="MEDIUM",
                message=f"{len(unassigned_tasks)} tasks have no assignee",
                evidence={"unassigned": [t.get("summary", t.get("name")) for t in unassigned_tasks]}
            ))
    
    if urgent_count > 2:
        dimensions["team_burnout"] = max(dimensions["team_burnout"], 70)
        signals.append(RiskSignal(
            dimension="Team Burnout",
            severity="HIGH",
            message=f"{urgent_count} urgent priority tasks - possible overload",
            evidence={"urgent_count": urgent_count}
        ))
    
    # 5. QUALITY COLLAPSE (bug ratio)
    bug_count = sum(1 for t in tasks if "bug" in t.get("summary", "").lower() or "bug" in t.get("name", "").lower())
    if bug_count > 0:
        bug_ratio = bug_count / total_tasks
        if bug_ratio > 0.3:
            dimensions["quality_collapse"] = 80
            signals.append(RiskSignal(
                dimension="Quality Collapse",
                severity="HIGH",
                message=f"{bug_count} bug-related tasks ({bug_ratio*100:.0f}% of sprint)",
                evidence={"bug_count": bug_count}
            ))
        elif bug_count >= 2:
            dimensions["quality_collapse"] = 40
            signals.append(RiskSignal(
                dimension="Quality Collapse",
                severity="MEDIUM",
                message=f"{bug_count} bug fixes in sprint",
                evidence={"bug_count": bug_count}
            ))
    
    # 6. FALSE REPORTING (no due dates on active work)
    if no_due_date_count > 0:
        no_date_ratio = no_due_date_count / total_tasks
        if no_date_ratio > 0.5:
            dimensions["false_reporting"] = 60
            signals.append(RiskSignal(
                dimension="False Reporting",
                severity="MEDIUM",
                message=f"{no_due_date_count} active tasks have no due date - progress tracking impaired",
                evidence={"no_due_date_count": no_due_date_count}
            ))
    
    # ============== OVERALL SCORE ==============
    
    # Weighted average of dimensions
    weights = {
        "delivery_risk": 0.25,
        "dependency_failure": 0.20,
        "scope_creep": 0.15,
        "quality_collapse": 0.15,
        "team_burnout": 0.15,
        "false_reporting": 0.10
    }
    
    overall_score = sum(dimensions[d] * weights[d] for d in dimensions)
    
    if overall_score >= 70:
        risk_level = RiskLevel.HIGH
    elif overall_score >= 40:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW
    
    # ============== RECOMMENDATIONS ==============
    
    recommendations = []
    
    if dimensions["delivery_risk"] >= 60:
        recommendations.append("🚨 Address overdue tasks immediately - consider scope reduction or deadline extension")
    
    if dimensions["dependency_failure"] >= 50:
        recommendations.append("🔗 Unblock stuck tasks - escalate blockers to leadership")
    
    if dimensions["scope_creep"] >= 50:
        recommendations.append("📋 Too many tasks not started - re-prioritize or move to backlog")
    
    if dimensions["team_burnout"] >= 50:
        recommendations.append("👥 Assign unassigned tasks and balance workload across team")
    
    if len(recommendations) == 0:
        recommendations.append("✅ Sprint health looks stable - maintain current pace")
    
    # ============== NARRATIVE ==============
    
    high_signals = [s for s in signals if s.severity == "HIGH"]
    narrative = f"Sprint '{sprint_name}' Risk Analysis:\n\n"
    
    if risk_level == RiskLevel.HIGH:
        narrative += f"⚠️ HIGH RISK DETECTED (Score: {overall_score:.0f}/100)\n\n"
        narrative += "Critical issues found:\n"
        for s in high_signals:
            narrative += f"• {s.message}\n"
    elif risk_level == RiskLevel.MEDIUM:
        narrative += f"⚡ MEDIUM RISK (Score: {overall_score:.0f}/100)\n\n"
        narrative += "Watch these areas:\n"
        for s in signals[:3]:
            narrative += f"• {s.message}\n"
    else:
        narrative += f"✅ LOW RISK (Score: {overall_score:.0f}/100)\n\n"
        narrative += "Sprint appears healthy.\n"
    
    narrative += f"\nStatus Distribution: {json.dumps(status_counts, indent=2)}"
    narrative += f"\nStory Points: {completed_points}/{total_points} completed ({completion_rate:.0f}%)"
    
    return RiskAnalysis(
        overall_score=int(overall_score),
        risk_level=risk_level,
        dimensions=dimensions,
        signals=signals,
        recommendations=recommendations,
        narrative=narrative
    )


def format_risk_report(analysis: RiskAnalysis) -> str:
    """Format the risk analysis as a readable report"""
    
    border = "=" * 60
    report = f"""
{border}
         🎯 DELIVERY RISK RADAR - ANALYSIS REPORT
{border}

OVERALL RISK: {analysis.risk_level.value} (Score: {analysis.overall_score}/100)

{'-' * 60}
RISK DIMENSIONS (0-100 scale):
{'-' * 60}
"""
    
    dimension_names = {
        "scope_creep": "📈 Scope Creep",
        "dependency_failure": "🔗 Dependency Failure", 
        "false_reporting": "📊 False Reporting",
        "quality_collapse": "🐛 Quality Collapse",
        "team_burnout": "😓 Team Burnout",
        "delivery_risk": "📅 Delivery Risk"
    }
    
    for dim, score in sorted(analysis.dimensions.items(), key=lambda x: -x[1]):
        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        label = dimension_names.get(dim, dim)
        report += f"  {label:25} [{bar}] {score:3}/100\n"
    
    report += f"""
{'-' * 60}
RISK SIGNALS DETECTED ({len(analysis.signals)}):
{'-' * 60}
"""
    
    for signal in analysis.signals:
        icon = "🔴" if signal.severity == "HIGH" else "🟡" if signal.severity == "MEDIUM" else "🟢"
        report += f"  {icon} [{signal.dimension}] {signal.message}\n"
    
    report += f"""
{'-' * 60}
RECOMMENDATIONS:
{'-' * 60}
"""
    for rec in analysis.recommendations:
        report += f"  {rec}\n"
    
    report += f"""
{border}
"""
    
    return report


# ============== MAIN TEST FUNCTION ==============

def run_test_with_data(tasks_data: List[Dict], sprint_name: str = "Test Sprint"):
    """Run risk analysis on provided task data"""
    
    print("\n🔍 Running Delivery Risk Radar Analysis...")
    print(f"   Analyzing {len(tasks_data)} tasks in '{sprint_name}'")
    
    analysis = analyze_sprint_risks(tasks_data, sprint_name)
    report = format_risk_report(analysis)
    
    print(report)
    
    return analysis


if __name__ == "__main__":
    # Sample test data matching user's ClickUp sandbox
    sample_tasks = [
        {
            "id": "86d1xdazj",
            "name": "[SP:2][BUG] Login Button Not Working on Safari",
            "summary": "[SP:2][BUG] Login Button Not Working on Safari",
            "status": "to do",
            "priority": "urgent",
            "due_date": "2025-02-10T00:00:00+00:00",  # Overdue
            "assignee": None
        },
        {
            "id": "86d1xdak7",
            "name": "[SP:5][FEAT] User Login with Social Media",
            "summary": "[SP:5][FEAT] User Login with Social Media",
            "status": "in progress",
            "priority": "high",
            "due_date": None,
            "assignee": None
        },
        {
            "id": "86d1xdb98",
            "name": "[SP:3][BUG] Slow Page Load",
            "summary": "[SP:3][BUG] Slow Page Load",
            "status": "to do",
            "priority": "high",
            "due_date": None,
            "assignee": None
        },
        {
            "id": "86d1xdbgj",
            "name": "[SP:8][FEAT] Payment Gateway Integration",
            "summary": "[SP:8][FEAT] Payment Gateway Integration",
            "status": "planning",
            "priority": "normal",
            "due_date": None,
            "assignee": None
        },
        {
            "id": "86d1xdbra",
            "name": "[SP:5][FEAT] User Profile Redesign",
            "summary": "[SP:5][FEAT] User Profile Redesign",
            "status": "in progress",
            "priority": "normal",
            "due_date": None,
            "assignee": None
        },
        {
            "id": "86d1xda2t",
            "name": "[SP:3][FEAT] Dashboard Widget for Bookings",
            "summary": "[SP:3][FEAT] Dashboard Widget for Bookings",
            "status": "to do",
            "priority": "normal",
            "due_date": "2025-02-17T00:00:00+00:00",
            "assignee": None
        }
    ]
    
    run_test_with_data(sample_tasks, "Sprint 1 (2/9 - 2/22)")
