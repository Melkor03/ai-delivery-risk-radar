"""
Delivery Risk Radar - Executive Report Generator v3.0
CEO-focused, actionable, 2-3 pages max
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime, timezone, timedelta
import re


# Brand Colors
BRAND_NAVY = colors.HexColor('#1E3A5F')
BRAND_BLUE = colors.HexColor('#3B82F6')
RISK_RED = colors.HexColor('#DC2626')
RISK_YELLOW = colors.HexColor('#F59E0B')
RISK_GREEN = colors.HexColor('#10B981')
GRAY_DARK = colors.HexColor('#374151')
GRAY_MEDIUM = colors.HexColor('#6B7280')
GRAY_LIGHT = colors.HexColor('#E5E7EB')
WHITE = colors.white


def parse_story_points(text):
    """Extract story points from [SP:X] pattern"""
    if not text:
        return 0
    match = re.search(r'\[SP:(\d+)\]', str(text))
    return int(match.group(1)) if match else 0


def calculate_task_risk(task):
    """Calculate risk score and flags for a task"""
    score = 0
    flags = []
    
    status = (task.get('status') or '').lower()
    is_done = status in ['complete', 'done', 'closed', 'resolved']
    
    # Check overdue
    due_date = task.get('due_date')
    if due_date and not is_done:
        try:
            if isinstance(due_date, str):
                due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            elif isinstance(due_date, (int, float)):
                due_dt = datetime.fromtimestamp(due_date/1000, tz=timezone.utc)
            else:
                due_dt = None
            
            if due_dt and due_dt < datetime.now(timezone.utc):
                days = (datetime.now(timezone.utc) - due_dt).days
                score += min(40, 20 + days * 5)
                flags.append(f"Overdue {days}d")
        except:
            pass
    
    # No due date for active tasks
    if not due_date and not is_done and status not in ['backlog', 'planning']:
        score += 15
        flags.append("No due date")
    
    # Blocked
    if task.get('blocked'):
        score += 25
        flags.append("Blocked")
    
    # Unassigned
    if not task.get('assignees'):
        score += 15
        flags.append("No owner")
    
    # Stale
    updated = task.get('updated') or task.get('date_updated')
    if updated and not is_done:
        try:
            if isinstance(updated, str):
                updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            elif isinstance(updated, (int, float)):
                updated_dt = datetime.fromtimestamp(updated/1000, tz=timezone.utc)
            else:
                updated_dt = None
            
            if updated_dt:
                days_stale = (datetime.now(timezone.utc) - updated_dt).days
                if days_stale > 7:
                    score += 10
                    flags.append(f"Stale {days_stale}d")
        except:
            pass
    
    level = 'HIGH' if score >= 50 else 'MEDIUM' if score >= 25 else 'LOW'
    return {'score': min(score, 100), 'level': level, 'flags': flags}


def analyze_tasks(tasks):
    """Comprehensive task analysis"""
    results = {
        'total': len(tasks),
        'completed': 0,
        'in_progress': 0,
        'blocked': 0,
        'overdue': 0,
        'unassigned': 0,
        'total_points': 0,
        'completed_points': 0,
        'high_risk': 0,
        'medium_risk': 0,
        'task_details': []
    }
    
    for t in tasks:
        name = t.get('summary') or t.get('name') or 'Unnamed Task'
        status = (t.get('status') or 'unknown').lower()
        points = parse_story_points(name) or t.get('story_points') or 0
        assignees = t.get('assignees', [])
        assignee = (assignees[0].get('username', 'Unassigned') if isinstance(assignees[0], dict) else assignees[0]) if assignees else 'Unassigned'
        
        results['total_points'] += points
        
        if status in ['complete', 'done', 'closed', 'resolved']:
            results['completed'] += 1
            results['completed_points'] += points
        elif status in ['in progress', 'in review', 'review', 'doing']:
            results['in_progress'] += 1
        
        if t.get('blocked'):
            results['blocked'] += 1
        
        if not assignees:
            results['unassigned'] += 1
        
        # Calculate risk
        risk = calculate_task_risk(t)
        
        if risk['level'] == 'HIGH':
            results['high_risk'] += 1
        elif risk['level'] == 'MEDIUM':
            results['medium_risk'] += 1
        
        if 'Overdue' in ' '.join(risk['flags']):
            results['overdue'] += 1
        
        results['task_details'].append({
            'name': name,
            'status': status.title(),
            'assignee': assignee,
            'points': points,
            'risk_level': risk['level'],
            'risk_score': risk['score'],
            'flags': risk['flags'],
            'url': t.get('url')
        })
    
    # Sort by risk score descending
    results['task_details'].sort(key=lambda x: x['risk_score'], reverse=True)
    
    return results


def get_action_for_task(task):
    """Generate specific action recommendation based on flags"""
    flags = task.get('flags', [])
    name = task.get('name', '')[:40]
    
    actions = []
    
    if 'No owner' in flags:
        actions.append(f"Assign owner immediately")
    
    if 'No due date' in flags:
        actions.append(f"Set target completion date")
    
    if 'Blocked' in flags:
        actions.append(f"Escalate blocker to remove impediment")
    
    for f in flags:
        if 'Overdue' in f:
            actions.append(f"Reprioritize or extend deadline")
            break
        if 'Stale' in f:
            actions.append(f"Check in with assignee on progress")
            break
    
    return actions[0] if actions else "Monitor progress"


def generate_ceo_report(
    organization_name: str = "Organization",
    project: dict = None,
    tasks: list = None,
    assessment: dict = None
) -> bytes:
    """Generate concise, actionable CEO report"""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6*inch,
        leftMargin=0.6*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=BRAND_NAVY,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=BRAND_NAVY,
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    subheader_style = ParagraphStyle(
        'Subheader',
        parent=styles['Normal'],
        fontSize=11,
        textColor=GRAY_DARK,
        spaceBefore=4,
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        textColor=GRAY_DARK,
        spaceBefore=2,
        spaceAfter=2
    )
    
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=8,
        textColor=GRAY_MEDIUM
    )
    
    # Analyze tasks
    analysis = analyze_tasks(tasks or [])
    
    # Determine overall health
    if analysis['high_risk'] >= 3 or analysis['overdue'] >= 3:
        health_status = "🔴 CRITICAL"
        health_color = RISK_RED
        health_bg = colors.HexColor('#FEE2E2')
    elif analysis['high_risk'] >= 1 or analysis['medium_risk'] >= 3 or analysis['overdue'] >= 1:
        health_status = "🟡 AT RISK"
        health_color = RISK_YELLOW
        health_bg = colors.HexColor('#FEF3C7')
    else:
        health_status = "🟢 HEALTHY"
        health_color = RISK_GREEN
        health_bg = colors.HexColor('#D1FAE5')
    
    # Calculate progress
    total_pts = analysis['total_points'] or analysis['total']
    done_pts = analysis['completed_points'] or analysis['completed']
    progress_pct = int(done_pts / total_pts * 100) if total_pts > 0 else 0
    
    story = []
    
    # ========== HEADER ==========
    project_name = project.get('name', organization_name) if project else organization_name
    
    header_data = [
        [
            Paragraph(f"<b>RISK RADAR</b> | {project_name}", ParagraphStyle('H', fontSize=12, textColor=BRAND_NAVY)),
            Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}", small_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[4*inch, 3*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 1, BRAND_NAVY),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 16))
    
    # ========== SPRINT HEALTH BOX ==========
    story.append(Paragraph("SPRINT HEALTH", header_style))
    
    # Health status box
    health_data = [[
        Paragraph(f"<b>{health_status}</b>", ParagraphStyle('HS', fontSize=18, textColor=health_color, alignment=TA_CENTER)),
    ]]
    health_table = Table(health_data, colWidths=[7*inch])
    health_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), health_bg),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    story.append(health_table)
    story.append(Spacer(1, 12))
    
    # Progress metrics row
    metrics_data = [[
        Paragraph(f"<b>{progress_pct}%</b><br/><font size='8' color='#6B7280'>Complete</font>", 
                  ParagraphStyle('M', fontSize=20, textColor=BRAND_NAVY, alignment=TA_CENTER)),
        Paragraph(f"<b>{done_pts}/{total_pts}</b><br/><font size='8' color='#6B7280'>Story Points</font>", 
                  ParagraphStyle('M', fontSize=20, textColor=BRAND_NAVY, alignment=TA_CENTER)),
        Paragraph(f"<b>{analysis['total']}</b><br/><font size='8' color='#6B7280'>Total Tasks</font>", 
                  ParagraphStyle('M', fontSize=20, textColor=BRAND_NAVY, alignment=TA_CENTER)),
        Paragraph(f"<b>{analysis['in_progress']}</b><br/><font size='8' color='#6B7280'>In Progress</font>", 
                  ParagraphStyle('M', fontSize=20, textColor=BRAND_NAVY, alignment=TA_CENTER)),
    ]]
    metrics_table = Table(metrics_data, colWidths=[1.75*inch, 1.75*inch, 1.75*inch, 1.75*inch])
    metrics_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), GRAY_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEAFTER', (0, 0), (2, 0), 1, WHITE),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 8))
    
    # Warning badges
    warnings = []
    if analysis['overdue'] > 0:
        warnings.append(f"⚠️ {analysis['overdue']} Overdue")
    if analysis['blocked'] > 0:
        warnings.append(f"🚫 {analysis['blocked']} Blocked")
    if analysis['unassigned'] > 0:
        warnings.append(f"👤 {analysis['unassigned']} Unassigned")
    
    if warnings:
        warning_text = "  |  ".join(warnings)
        story.append(Paragraph(warning_text, ParagraphStyle('W', fontSize=10, textColor=RISK_RED, alignment=TA_CENTER)))
        story.append(Spacer(1, 12))
    
    # ========== TOP ACTIONS NEEDED ==========
    at_risk_tasks = [t for t in analysis['task_details'] if t['risk_level'] in ['HIGH', 'MEDIUM']]
    
    if at_risk_tasks:
        story.append(Paragraph("🚨 TOP ACTIONS NEEDED", header_style))
        
        action_rows = []
        for i, task in enumerate(at_risk_tasks[:5], 1):
            # Risk badge color
            if task['risk_level'] == 'HIGH':
                badge_color = RISK_RED
                badge_bg = '#FEE2E2'
            else:
                badge_color = RISK_YELLOW
                badge_bg = '#FEF3C7'
            
            # Task name (truncate if needed)
            task_name = task['name'][:50] + ('...' if len(task['name']) > 50 else '')
            
            # Flags as readable text
            issues = ", ".join(task['flags']) if task['flags'] else "Monitor"
            
            # Get specific action
            action = get_action_for_task(task)
            
            action_rows.append([
                Paragraph(f"<b>{i}.</b>", body_style),
                Paragraph(f"<b>{task_name}</b><br/><font size='8' color='#DC2626'>❌ {issues}</font><br/><font size='9' color='#059669'>→ {action}</font>", body_style),
                Paragraph(f"<font color='{badge_color}'><b>{task['risk_level']}</b></font>", 
                          ParagraphStyle('B', fontSize=9, alignment=TA_CENTER)),
                Paragraph(f"{task['points']} pts" if task['points'] else "-", small_style),
            ])
        
        action_table = Table(action_rows, colWidths=[0.3*inch, 5*inch, 0.8*inch, 0.7*inch])
        action_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, GRAY_LIGHT),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F9FAFB')),
        ]))
        story.append(action_table)
    else:
        story.append(Paragraph("✅ ALL TASKS ON TRACK", header_style))
        story.append(Paragraph("No immediate actions required. Continue regular monitoring.", body_style))
    
    story.append(Spacer(1, 16))
    
    # ========== QUICK STATS SUMMARY ==========
    story.append(Paragraph("📊 SUMMARY BY STATUS", header_style))
    
    # Stats table
    stats_data = [
        ['Status', 'Count', 'Story Points'],
        ['✅ Completed', str(analysis['completed']), str(analysis['completed_points'])],
        ['🔄 In Progress', str(analysis['in_progress']), '-'],
        ['📋 To Do', str(analysis['total'] - analysis['completed'] - analysis['in_progress']), '-'],
        ['🚫 Blocked', str(analysis['blocked']), '-'],
        ['⚠️ At Risk (H+M)', str(analysis['high_risk'] + analysis['medium_risk']), '-'],
    ]
    
    stats_table = Table(stats_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, GRAY_LIGHT),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#D1FAE5')),  # Green for completed
    ]))
    story.append(stats_table)
    
    # ========== PAGE BREAK - FULL TASK LIST ==========
    if len(analysis['task_details']) > 5:
        story.append(PageBreak())
        story.append(Paragraph("📋 COMPLETE TASK LIST", header_style))
        
        task_rows = [['Task', 'Status', 'Owner', 'Pts', 'Risk', 'Issues']]
        
        for task in analysis['task_details']:
            # Risk color
            if task['risk_level'] == 'HIGH':
                risk_display = f"<font color='#DC2626'><b>HIGH</b></font>"
            elif task['risk_level'] == 'MEDIUM':
                risk_display = f"<font color='#F59E0B'><b>MED</b></font>"
            else:
                risk_display = f"<font color='#10B981'>LOW</font>"
            
            task_rows.append([
                Paragraph(task['name'][:35] + ('...' if len(task['name']) > 35 else ''), 
                          ParagraphStyle('T', fontSize=8)),
                task['status'][:10],
                task['assignee'][:12],
                str(task['points']) if task['points'] else '-',
                Paragraph(risk_display, ParagraphStyle('R', fontSize=8)),
                Paragraph(', '.join(task['flags'][:2]) if task['flags'] else '✓', 
                          ParagraphStyle('F', fontSize=7, textColor=GRAY_MEDIUM)),
            ])
        
        task_table = Table(task_rows, colWidths=[2.2*inch, 0.8*inch, 1*inch, 0.4*inch, 0.5*inch, 1.5*inch])
        task_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (3, 0), (4, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, GRAY_LIGHT),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#F9FAFB')]),
        ]))
        story.append(task_table)
    
    # ========== FOOTER ==========
    story.append(Spacer(1, 24))
    story.append(Paragraph(
        f"<i>Report generated by Delivery Risk Radar | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | Confidential</i>",
        ParagraphStyle('Footer', fontSize=8, textColor=GRAY_MEDIUM, alignment=TA_CENTER)
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# Wrapper for backward compatibility
def generate_enhanced_executive_report(
    organization_name: str = "Organization",
    projects: list = None,
    assessments: list = None,
    tasks: list = None,
    **kwargs
) -> bytes:
    """Wrapper to maintain API compatibility"""
    project = projects[0] if projects else None
    assessment = assessments[0] if assessments else None
    
    return generate_ceo_report(
        organization_name=organization_name,
        project=project,
        tasks=tasks,
        assessment=assessment
    )
