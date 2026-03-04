# report_generator.py - Enhanced Executive PDF Report Generator
# Version 2.0 - Task-Level Intelligence

import io
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, HRFlowable, KeepTogether, ListFlowable, ListItem
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderPDF
import re

# Color palette
COLORS = {
    'primary': colors.HexColor('#1E3A5F'),
    'secondary': colors.HexColor('#2D5F8B'),
    'accent': colors.HexColor('#3B82F6'),
    'high_risk': colors.HexColor('#DC2626'),
    'medium_risk': colors.HexColor('#F59E0B'),
    'low_risk': colors.HexColor('#10B981'),
    'neutral': colors.HexColor('#6B7280'),
    'background': colors.HexColor('#F8FAFC'),
    'text': colors.HexColor('#1F2937'),
    'text_light': colors.HexColor('#6B7280'),
    'border': colors.HexColor('#E5E7EB'),
    'overdue': colors.HexColor('#EF4444'),
    'blocked': colors.HexColor('#7C3AED'),
    'unassigned': colors.HexColor('#F97316'),
}

# Risk flag icons (unicode)
RISK_FLAGS = {
    'overdue': '⏰',
    'blocked': '🚫',
    'unassigned': '👤',
    'no_due_date': '📅',
    'stale': '💤',
    'high_points': '📈',
    'scope_creep': '📊',
}


def get_risk_color(level: str) -> colors.Color:
    level = (level or '').upper()
    if level == 'HIGH':
        return COLORS['high_risk']
    elif level == 'MEDIUM':
        return COLORS['medium_risk']
    elif level == 'LOW':
        return COLORS['low_risk']
    return COLORS['neutral']


def parse_story_points(task_name: str) -> Optional[int]:
    """Extract story points from task name like [SP:5]"""
    match = re.search(r'\[SP:(\d+)\]', task_name)
    if match:
        return int(match.group(1))
    return None


def calculate_task_risk_score(task: Dict) -> Dict:
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
            else:
                due_dt = datetime.fromtimestamp(due_date/1000, tz=timezone.utc)
            
            status = (task.get('status') or '').lower()
            if status not in ['complete', 'done', 'closed', 'resolved']:
                if due_dt < now:
                    days_overdue = (now - due_dt).days
                    score += min(40, 20 + days_overdue * 5)
                    flags.append(('overdue', f'Overdue by {days_overdue} days'))
                elif due_dt < now + timedelta(days=2):
                    score += 10
                    flags.append(('due_soon', 'Due within 2 days'))
        except:
            pass
    else:
        # No due date
        status = (task.get('status') or '').lower()
        if status not in ['complete', 'done', 'closed', 'resolved', 'backlog']:
            score += 15
            flags.append(('no_due_date', 'No due date set'))
    
    # Check blocked
    if task.get('blocked'):
        score += 25
        flags.append(('blocked', 'Task is blocked'))
    
    # Check unassigned
    assignees = task.get('assignees', [])
    if not assignees or len(assignees) == 0:
        score += 15
        flags.append(('unassigned', 'No assignee'))
    
    # Check stale (no updates in 7+ days)
    updated = task.get('date_updated')
    if updated:
        try:
            if isinstance(updated, str):
                updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            else:
                updated_dt = datetime.fromtimestamp(updated/1000, tz=timezone.utc)
            
            days_stale = (now - updated_dt).days
            if days_stale > 7:
                score += 10
                flags.append(('stale', f'No updates in {days_stale} days'))
        except:
            pass
    
    # High story points in progress late in sprint
    points = task.get('story_points') or parse_story_points(task.get('name', ''))
    if points and points >= 8:
        status = (task.get('status') or '').lower()
        if status in ['to do', 'todo', 'open', 'planning']:
            score += 15
            flags.append(('high_points', f'High complexity ({points} points) not started'))
    
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


def create_styles():
    """Create custom paragraph styles"""
    from reportlab.lib.styles import StyleSheet1
    
    styles = StyleSheet1()
    styles.add(ParagraphStyle(name='Normal', fontSize=10, leading=12))
    styles.add(ParagraphStyle(name='Heading1', parent=styles['Normal'], fontSize=18, leading=22, spaceAfter=6, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Heading2', parent=styles['Normal'], fontSize=14, leading=18, spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Heading3', parent=styles['Normal'], fontSize=12, leading=14, spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold'))
    
    styles.add(ParagraphStyle(name='ReportTitle', parent=styles['Heading1'], fontSize=28, spaceAfter=30, textColor=COLORS['primary'], alignment=TA_CENTER, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='ReportSubtitle', parent=styles['Normal'], fontSize=14, spaceAfter=20, textColor=COLORS['text_light'], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='SectionHeader', parent=styles['Heading2'], fontSize=16, spaceBefore=20, spaceAfter=12, textColor=COLORS['primary'], fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SubsectionHeader', parent=styles['Heading3'], fontSize=13, spaceBefore=15, spaceAfter=8, textColor=COLORS['secondary'], fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='BodyText', parent=styles['Normal'], fontSize=10, spaceAfter=8, textColor=COLORS['text'], alignment=TA_JUSTIFY, leading=14))
    styles.add(ParagraphStyle(name='SmallText', parent=styles['Normal'], fontSize=8, textColor=COLORS['text_light'], leading=10))
    styles.add(ParagraphStyle(name='Recommendation', parent=styles['Normal'], fontSize=10, spaceAfter=6, textColor=COLORS['text'], leftIndent=20, bulletIndent=10, leading=14))
    styles.add(ParagraphStyle(name='MetricValue', parent=styles['Normal'], fontSize=24, fontName='Helvetica-Bold', textColor=COLORS['primary'], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='MetricLabel', parent=styles['Normal'], fontSize=9, textColor=COLORS['text_light'], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='TaskName', parent=styles['Normal'], fontSize=9, textColor=COLORS['text'], leading=11))
    styles.add(ParagraphStyle(name='RiskFlag', parent=styles['Normal'], fontSize=8, textColor=COLORS['high_risk'], leading=10))
    
    return styles


def create_header_footer(canvas, doc, title: str, generated_at: str):
    """Add header and footer to each page"""
    canvas.saveState()
    
    # Header
    canvas.setFillColor(COLORS['primary'])
    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawString(inch, doc.pagesize[1] - 0.5*inch, "DELIVERY RISK RADAR")
    
    canvas.setFillColor(COLORS['text_light'])
    canvas.setFont('Helvetica', 9)
    canvas.drawRightString(doc.pagesize[0] - inch, doc.pagesize[1] - 0.5*inch, title)
    
    # Footer
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(COLORS['text_light'])
    canvas.drawString(inch, 0.5*inch, f"Generated: {generated_at}")
    canvas.drawCentredString(doc.pagesize[0]/2, 0.5*inch, "CONFIDENTIAL - FOR INTERNAL USE ONLY")
    canvas.drawRightString(doc.pagesize[0] - inch, 0.5*inch, f"Page {doc.page}")
    
    # Header line
    canvas.setStrokeColor(COLORS['border'])
    canvas.setLineWidth(0.5)
    canvas.line(inch, doc.pagesize[1] - 0.6*inch, doc.pagesize[0] - inch, doc.pagesize[1] - 0.6*inch)
    
    canvas.restoreState()


def create_burndown_chart(tasks: List[Dict], sprint_start: str, sprint_end: str) -> Drawing:
    """Create a sprint burndown chart"""
    drawing = Drawing(400, 200)
    
    # Calculate data
    total_points = sum(t.get('story_points', 0) or parse_story_points(t.get('name', '')) or 0 for t in tasks)
    
    if total_points == 0:
        # No story points, show task count instead
        total_points = len(tasks)
    
    # Create chart
    chart = LinePlot()
    chart.x = 50
    chart.y = 30
    chart.width = 320
    chart.height = 140
    
    # Ideal line (straight diagonal)
    try:
        start_dt = datetime.fromisoformat(sprint_start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(sprint_end.replace('Z', '+00:00'))
        sprint_days = (end_dt - start_dt).days or 14
    except:
        sprint_days = 14
    
    ideal_line = [(i, total_points - (total_points * i / sprint_days)) for i in range(sprint_days + 1)]
    
    # Actual line (simplified - show current state)
    completed = sum(1 for t in tasks if (t.get('status') or '').lower() in ['complete', 'done', 'closed'])
    remaining = total_points - completed
    
    now = datetime.now(timezone.utc)
    try:
        start_dt = datetime.fromisoformat(sprint_start.replace('Z', '+00:00'))
        days_elapsed = (now - start_dt).days
    except:
        days_elapsed = 7
    
    actual_line = [(0, total_points), (days_elapsed, remaining)]
    
    chart.data = [ideal_line, actual_line]
    
    # Style
    chart.lines[0].strokeColor = COLORS['neutral']
    chart.lines[0].strokeDashArray = [4, 2]
    chart.lines[0].strokeWidth = 1
    chart.lines[1].strokeColor = COLORS['accent']
    chart.lines[1].strokeWidth = 2
    
    chart.xValueAxis.valueMin = 0
    chart.xValueAxis.valueMax = sprint_days
    chart.xValueAxis.labelTextFormat = '%d'
    
    chart.yValueAxis.valueMin = 0
    chart.yValueAxis.valueMax = total_points + 5
    
    drawing.add(chart)
    
    # Legend
    drawing.add(String(60, 180, "Burndown Chart", fontSize=10, fontName='Helvetica-Bold', fillColor=COLORS['text']))
    drawing.add(Line(280, 180, 300, 180, strokeColor=COLORS['neutral'], strokeDashArray=[4,2]))
    drawing.add(String(305, 177, "Ideal", fontSize=8, fillColor=COLORS['text_light']))
    drawing.add(Line(280, 165, 300, 165, strokeColor=COLORS['accent'], strokeWidth=2))
    drawing.add(String(305, 162, "Actual", fontSize=8, fillColor=COLORS['text_light']))
    
    return drawing


def create_risk_distribution_pie(tasks: List[Dict]) -> Drawing:
    """Create pie chart showing task risk distribution"""
    drawing = Drawing(200, 150)
    
    # Calculate risk distribution
    high = medium = low = 0
    for task in tasks:
        risk = calculate_task_risk_score(task)
        if risk['level'] == 'HIGH':
            high += 1
        elif risk['level'] == 'MEDIUM':
            medium += 1
        else:
            low += 1
    
    total = high + medium + low or 1
    
    pie = Pie()
    pie.x = 50
    pie.y = 20
    pie.width = 100
    pie.height = 100
    pie.data = [high, medium, low]
    pie.labels = [f'High ({high})', f'Medium ({medium})', f'Low ({low})']
    pie.slices.strokeWidth = 0.5
    pie.slices[0].fillColor = COLORS['high_risk']
    pie.slices[1].fillColor = COLORS['medium_risk']
    pie.slices[2].fillColor = COLORS['low_risk']
    pie.slices.fontName = 'Helvetica'
    pie.slices.fontSize = 8
    
    drawing.add(pie)
    drawing.add(String(50, 130, "Task Risk Distribution", fontSize=10, fontName='Helvetica-Bold', fillColor=COLORS['text']))
    
    return drawing


def generate_task_risk_table(tasks: List[Dict], styles) -> List:
    """Generate task risk table section"""
    elements = []
    
    # Sort tasks by risk score
    tasks_with_risk = []
    for task in tasks:
        risk = calculate_task_risk_score(task)
        tasks_with_risk.append({**task, '_risk': risk})
    
    tasks_with_risk.sort(key=lambda x: x['_risk']['score'], reverse=True)
    
    # Table header
    table_data = [['Task', 'Status', 'Assignee', 'Due', 'Points', 'Risk', 'Flags']]
    
    for task in tasks_with_risk[:25]:  # Top 25 tasks
        risk = task['_risk']
        
        # Task name (truncated)
        name = task.get('name', 'Unknown')[:35]
        if len(task.get('name', '')) > 35:
            name += '...'
        
        # Status
        status = task.get('status', 'N/A')[:12]
        
        # Assignee
        assignees = task.get('assignees', [])
        if assignees:
            assignee = assignees[0].get('username', assignees[0].get('email', 'N/A'))[:12]
        else:
            assignee = 'Unassigned'
        
        # Due date
        due_date = task.get('due_date')
        if due_date:
            try:
                if isinstance(due_date, str):
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                else:
                    due_dt = datetime.fromtimestamp(due_date/1000, tz=timezone.utc)
                due_str = due_dt.strftime('%m/%d')
            except:
                due_str = 'N/A'
        else:
            due_str = 'None'
        
        # Story points
        points = task.get('story_points') or parse_story_points(task.get('name', '')) or '-'
        
        # Risk level with color indicator
        risk_level = risk['level']
        
        # Risk flags (abbreviated)
        flags = ', '.join([f[0][:3].upper() for f in risk['flags'][:3]]) or '-'
        
        table_data.append([name, status, assignee, due_str, str(points), risk_level, flags])
    
    if len(table_data) > 1:
        task_table = Table(table_data, colWidths=[2*inch, 0.8*inch, 0.9*inch, 0.5*inch, 0.4*inch, 0.5*inch, 0.7*inch])
        
        table_style = [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        
        # Color code risk level cells
        for i, row in enumerate(table_data[1:], 1):
            risk = row[5].upper()
            if risk == 'HIGH':
                table_style.append(('TEXTCOLOR', (5, i), (5, i), COLORS['high_risk']))
                table_style.append(('FONTNAME', (5, i), (5, i), 'Helvetica-Bold'))
                table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#FEF2F2')))
            elif risk == 'MEDIUM':
                table_style.append(('TEXTCOLOR', (5, i), (5, i), COLORS['medium_risk']))
                table_style.append(('FONTNAME', (5, i), (5, i), 'Helvetica-Bold'))
            elif risk == 'LOW':
                table_style.append(('TEXTCOLOR', (5, i), (5, i), COLORS['low_risk']))
        
        task_table.setStyle(TableStyle(table_style))
        elements.append(task_table)
        
        # Legend
        elements.append(Spacer(1, 0.15*inch))
        legend_text = "<b>Risk Flags:</b> OVE=Overdue, BLO=Blocked, UNA=Unassigned, NOD=No Due Date, STA=Stale, HIG=High Points"
        elements.append(Paragraph(legend_text, styles['SmallText']))
    
    return elements


def generate_sprint_summary(tasks: List[Dict], styles) -> List:
    """Generate sprint progress summary"""
    elements = []
    
    # Calculate metrics
    total_tasks = len(tasks)
    total_points = 0
    completed_points = 0
    completed_tasks = 0
    in_progress = 0
    blocked = 0
    overdue = 0
    unassigned = 0
    
    now = datetime.now(timezone.utc)
    
    for task in tasks:
        points = task.get('story_points') or parse_story_points(task.get('name', '')) or 0
        total_points += points
        
        status = (task.get('status') or '').lower()
        if status in ['complete', 'done', 'closed', 'resolved']:
            completed_tasks += 1
            completed_points += points
        elif status in ['in progress', 'in review', 'review']:
            in_progress += 1
        
        if task.get('blocked'):
            blocked += 1
        
        if not task.get('assignees'):
            unassigned += 1
        
        due_date = task.get('due_date')
        if due_date and status not in ['complete', 'done', 'closed']:
            try:
                if isinstance(due_date, str):
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                else:
                    due_dt = datetime.fromtimestamp(due_date/1000, tz=timezone.utc)
                if due_dt < now:
                    overdue += 1
            except:
                pass
    
    # Metrics table
    completion_pct = int((completed_points / total_points * 100) if total_points > 0 else (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0)
    
    metrics_data = [
        ['Total Tasks', 'Completed', 'In Progress', 'Story Points', 'Completion'],
        [str(total_tasks), str(completed_tasks), str(in_progress), f"{completed_points}/{total_points}", f"{completion_pct}%"]
    ]
    
    metrics_table = Table(metrics_data, colWidths=[1.2*inch]*5)
    metrics_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 16),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLORS['text_light']),
        ('TEXTCOLOR', (0, 1), (-1, 1), COLORS['primary']),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, -1), COLORS['background']),
        ('BOX', (0, 0), (-1, -1), 1, COLORS['border']),
    ]))
    elements.append(metrics_table)
    
    # Warning metrics
    elements.append(Spacer(1, 0.15*inch))
    
    warnings = []
    if overdue > 0:
        warnings.append(f"<font color='#DC2626'><b>⚠ {overdue} overdue task(s)</b></font>")
    if blocked > 0:
        warnings.append(f"<font color='#7C3AED'><b>🚫 {blocked} blocked task(s)</b></font>")
    if unassigned > 0:
        warnings.append(f"<font color='#F97316'><b>👤 {unassigned} unassigned task(s)</b></font>")
    
    if warnings:
        warning_text = " | ".join(warnings)
        elements.append(Paragraph(warning_text, styles['BodyText']))
    
    return elements


def generate_at_risk_tasks_section(tasks: List[Dict], styles) -> List:
    """Generate detailed at-risk tasks section with recommendations"""
    elements = []
    
    # Get high risk tasks
    high_risk_tasks = []
    for task in tasks:
        risk = calculate_task_risk_score(task)
        if risk['level'] == 'HIGH':
            high_risk_tasks.append({**task, '_risk': risk})
    
    high_risk_tasks.sort(key=lambda x: x['_risk']['score'], reverse=True)
    
    if high_risk_tasks:
        elements.append(Paragraph(f"<b>⚠ {len(high_risk_tasks)} High-Risk Tasks Requiring Immediate Attention</b>", styles['SubsectionHeader']))
        elements.append(Spacer(1, 0.1*inch))
        
        for i, task in enumerate(high_risk_tasks[:10], 1):
            risk = task['_risk']
            name = task.get('name', 'Unknown')
            
            # Task header
            elements.append(Paragraph(f"<b>{i}. {name}</b>", styles['BodyText']))
            
            # Risk flags
            flags_text = []
            for flag_type, flag_desc in risk['flags']:
                flags_text.append(f"• {flag_desc}")
            
            if flags_text:
                elements.append(Paragraph(f"<font color='#DC2626'>Issues: {'; '.join([f[1] for f in risk['flags']])}</font>", styles['SmallText']))
            
            # Recommendation based on flags
            recs = []
            for flag_type, _ in risk['flags']:
                if flag_type == 'overdue':
                    recs.append("Escalate and reassess timeline")
                elif flag_type == 'blocked':
                    recs.append("Identify and resolve blocker")
                elif flag_type == 'unassigned':
                    recs.append("Assign owner immediately")
                elif flag_type == 'no_due_date':
                    recs.append("Set realistic due date")
                elif flag_type == 'stale':
                    recs.append("Check status and update")
            
            if recs:
                elements.append(Paragraph(f"<font color='#2D5F8B'>→ Recommended: {'; '.join(list(set(recs))[:3])}</font>", styles['SmallText']))
            
            elements.append(Spacer(1, 0.1*inch))
    else:
        elements.append(Paragraph("✓ No high-risk tasks identified. Continue monitoring.", styles['BodyText']))
    
    return elements


def generate_enhanced_executive_report(
    organization_name: str,
    projects: List[Dict],
    assessments: List[Dict],
    tasks: List[Dict] = None,
    trends: List[Dict] = None,
    sprint_info: Dict = None
) -> bytes:
    """Generate comprehensive executive PDF report with task-level details"""
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    styles = create_styles()
    story = []
    generated_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    
    # ==================== COVER PAGE ====================
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("DELIVERY RISK RADAR", styles['ReportTitle']))
    story.append(Paragraph("Executive Risk Assessment Report", styles['ReportSubtitle']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(organization_name, styles['SubsectionHeader']))
    story.append(Paragraph(f"Report Period: {datetime.now().strftime('%B %Y')}", styles['BodyText']))
    story.append(Paragraph(f"Generated: {generated_at}", styles['BodyText']))
    story.append(Spacer(1, 1.5*inch))
    
    # Confidentiality notice
    story.append(HRFlowable(width="60%", thickness=1, color=COLORS['border'], spaceAfter=15))
    story.append(Paragraph("<b>CONFIDENTIAL</b>", ParagraphStyle('Conf', parent=styles['Normal'], alignment=TA_CENTER, textColor=COLORS['high_risk'])))
    story.append(Paragraph("This document contains sensitive business information intended for executive leadership only.", 
                          ParagraphStyle('ConfNote', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=COLORS['text_light'])))
    
    story.append(PageBreak())
    
    # ==================== EXECUTIVE SUMMARY ====================
    story.append(Paragraph("1. Executive Summary", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
    
    # Project metrics
    total_projects = len(projects)
    high_risk = sum(1 for p in projects if (p.get('risk_level') or '').upper() == 'HIGH')
    medium_risk = sum(1 for p in projects if (p.get('risk_level') or '').upper() == 'MEDIUM')
    low_risk = sum(1 for p in projects if (p.get('risk_level') or '').upper() == 'LOW')
    
    metrics_data = [
        [str(total_projects), str(high_risk), str(medium_risk), str(low_risk)],
        ['Total Projects', 'High Risk', 'Medium Risk', 'Low Risk']
    ]
    metrics_table = Table(metrics_data, colWidths=[1.5*inch]*4)
    metrics_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 28),
        ('FONTSIZE', (0, 1), (-1, 1), 10),
        ('TEXTCOLOR', (0, 0), (0, 0), COLORS['primary']),
        ('TEXTCOLOR', (1, 0), (1, 0), COLORS['high_risk']),
        ('TEXTCOLOR', (2, 0), (2, 0), COLORS['medium_risk']),
        ('TEXTCOLOR', (3, 0), (3, 0), COLORS['low_risk']),
        ('TEXTCOLOR', (0, 1), (-1, 1), COLORS['text_light']),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Status assessment
    if high_risk > 0:
        status = f"<font color='#DC2626'><b>ALERT:</b></font> {high_risk} project(s) require immediate executive attention."
    elif medium_risk > 0:
        status = f"<font color='#F59E0B'><b>CAUTION:</b></font> {medium_risk} project(s) require active monitoring."
    else:
        status = "<font color='#10B981'><b>HEALTHY:</b></font> All projects operating within acceptable risk parameters."
    story.append(Paragraph(status, styles['BodyText']))
    story.append(Spacer(1, 0.3*inch))
    
    # ==================== SPRINT PROGRESS (if tasks provided) ====================
    if tasks:
        story.append(Paragraph("2. Sprint Progress & Task Analysis", styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
        
        # Sprint summary metrics
        story.append(Paragraph("<b>Sprint Overview</b>", styles['SubsectionHeader']))
        story.extend(generate_sprint_summary(tasks, styles))
        story.append(Spacer(1, 0.3*inch))
        
        # Burndown chart
        if sprint_info:
            try:
                chart = create_burndown_chart(
                    tasks, 
                    sprint_info.get('start_date', datetime.now().isoformat()),
                    sprint_info.get('end_date', (datetime.now() + timedelta(days=14)).isoformat())
                )
                story.append(chart)
                story.append(Spacer(1, 0.2*inch))
            except Exception as e:
                pass
        
        # At-risk tasks
        story.append(Paragraph("<b>At-Risk Tasks</b>", styles['SubsectionHeader']))
        story.extend(generate_at_risk_tasks_section(tasks, styles))
        
        story.append(PageBreak())
        
        # Full task risk table
        story.append(Paragraph("3. Complete Task Risk Assessment", styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
        story.extend(generate_task_risk_table(tasks, styles))
        
        story.append(PageBreak())
    
    # ==================== PROJECT PORTFOLIO ====================
    section_num = 4 if tasks else 2
    story.append(Paragraph(f"{section_num}. Project Portfolio Summary", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
    
    table_data = [['Project Name', 'Risk Level', 'Risk Score', 'Team Lead', 'Target End', 'Last Analyzed']]
    
    for project in sorted(projects, key=lambda x: x.get('risk_score', 0), reverse=True):
        risk_level = project.get('risk_level', 'N/A')
        table_data.append([
            project.get('name', 'Unknown')[:30],
            risk_level,
            f"{project.get('risk_score', 0)}%",
            (project.get('team_lead') or 'N/A')[:15],
            project.get('target_end_date', 'N/A'),
            project.get('last_analyzed', 'Never')[:10] if project.get('last_analyzed') else 'Never'
        ])
    
    if len(table_data) > 1:
        projects_table = Table(table_data, colWidths=[1.8*inch, 0.8*inch, 0.7*inch, 1*inch, 0.9*inch, 0.9*inch])
        
        table_style = [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]
        
        for i, row in enumerate(table_data[1:], 1):
            risk = row[1].upper() if row[1] else ''
            if risk == 'HIGH':
                table_style.append(('TEXTCOLOR', (1, i), (1, i), COLORS['high_risk']))
                table_style.append(('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'))
            elif risk == 'MEDIUM':
                table_style.append(('TEXTCOLOR', (1, i), (1, i), COLORS['medium_risk']))
            elif risk == 'LOW':
                table_style.append(('TEXTCOLOR', (1, i), (1, i), COLORS['low_risk']))
        
        projects_table.setStyle(TableStyle(table_style))
        story.append(projects_table)
    
    # ==================== RISK DIMENSIONS ====================
    section_num += 1
    if assessments:
        story.append(PageBreak())
        story.append(Paragraph(f"{section_num}. Enterprise Risk Dimensions Analysis", styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
        
        dimensions = {
            'Scope Creep': [], 'Dependency Failure': [], 'False Reporting': [],
            'Quality Collapse': [], 'Team Burnout': [], 'Vendor Risk': []
        }
        
        for assessment in assessments:
            dims = assessment.get('risk_dimensions', {})
            if dims:
                dimensions['Scope Creep'].append(dims.get('scope_creep', 0))
                dimensions['Dependency Failure'].append(dims.get('dependency_failure', 0))
                dimensions['False Reporting'].append(dims.get('false_reporting', 0))
                dimensions['Quality Collapse'].append(dims.get('quality_collapse', 0))
                dimensions['Team Burnout'].append(dims.get('burnout', 0))
                dimensions['Vendor Risk'].append(dims.get('vendor_risk', 0))
        
        dim_table_data = [['Risk Dimension', 'Avg Score', 'Max Score', 'Assessment']]
        for dim_name, values in dimensions.items():
            if values:
                avg = sum(values) / len(values)
                max_val = max(values)
                assessment_text = 'Critical' if avg >= 70 else 'Elevated' if avg >= 40 else 'Acceptable'
                dim_table_data.append([dim_name, f"{avg:.0f}%", f"{max_val:.0f}%", assessment_text])
        
        if len(dim_table_data) > 1:
            dim_table = Table(dim_table_data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 1.5*inch])
            dim_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, 0), COLORS['secondary']),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(dim_table)
    
    # ==================== RECOMMENDATIONS ====================
    section_num += 1
    story.append(PageBreak())
    story.append(Paragraph(f"{section_num}. Strategic Recommendations", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
    
    # Task-specific recommendations if we have tasks
    if tasks:
        story.append(Paragraph("<b>Immediate Actions (Task-Level):</b>", styles['BodyText']))
        
        # Generate specific recommendations from task analysis
        task_recs = []
        overdue_tasks = [t for t in tasks if calculate_task_risk_score(t)['level'] == 'HIGH']
        
        for task in overdue_tasks[:5]:
            name = task.get('name', 'Unknown')[:40]
            risk = calculate_task_risk_score(task)
            primary_issue = risk['flags'][0][1] if risk['flags'] else 'High risk'
            task_recs.append(f"<b>{name}</b>: {primary_issue}")
        
        for rec in task_recs:
            story.append(Paragraph(f"• {rec}", styles['Recommendation']))
        
        story.append(Spacer(1, 0.2*inch))
    
    # Standard recommendations
    story.append(Paragraph("<b>Ongoing Governance Recommendations:</b>", styles['BodyText']))
    standard_recs = [
        "Conduct weekly risk review meetings for all HIGH risk projects",
        "Implement mandatory status report validation against delivery metrics",
        "Establish escalation protocols with defined response time SLAs",
        "Schedule bi-weekly steering committee reviews for at-risk portfolios",
        "Deploy automated risk monitoring to detect early warning signals"
    ]
    for rec in standard_recs:
        story.append(Paragraph(f"• {rec}", styles['Recommendation']))
    
    # ==================== APPENDIX ====================
    story.append(PageBreak())
    story.append(Paragraph("Appendix: Methodology & Data Sources", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
    
    methodology = """
    <b>Risk Assessment Methodology</b><br/><br/>
    
    This report utilizes AI-powered analysis combined with rule-based task assessment to evaluate delivery risk. 
    Task-level risk scores are calculated using:<br/><br/>
    
    • <b>Overdue Status:</b> +20-40 points for tasks past due date<br/>
    • <b>Blocked Status:</b> +25 points for blocked tasks<br/>
    • <b>Unassigned:</b> +15 points for tasks without owners<br/>
    • <b>Missing Due Date:</b> +15 points for in-progress tasks without deadlines<br/>
    • <b>Stale Tasks:</b> +10 points for no updates in 7+ days<br/>
    • <b>High Complexity:</b> +15 points for 8+ story point tasks not started<br/><br/>
    
    <b>Task Risk Classification:</b><br/>
    • HIGH (50-100): Immediate intervention required<br/>
    • MEDIUM (25-49): Active monitoring needed<br/>
    • LOW (0-24): On track<br/>
    """
    story.append(Paragraph(methodology, styles['BodyText']))
    
    # Build PDF
    def first_page(canvas, doc):
        pass
    
    def later_pages(canvas, doc):
        create_header_footer(canvas, doc, "Executive Risk Report", generated_at)
    
    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages)
    
    buffer.seek(0)
    return buffer.getvalue()


# Keep the original function for backward compatibility
def generate_executive_report(
    organization_name: str,
    projects: List[Dict],
    assessments: List[Dict]
) -> bytes:
    """Generate executive PDF report (backward compatible)"""
    return generate_enhanced_executive_report(
        organization_name=organization_name,
        projects=projects,
        assessments=assessments,
        tasks=None,
        trends=None,
        sprint_info=None
    )
