# report_generator.py - Executive PDF Report Generator

import io
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, HRFlowable, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF

# Color palette
COLORS = {
    'primary': colors.HexColor('#1E3A5F'),      # Deep navy
    'secondary': colors.HexColor('#2D5F8B'),    # Steel blue
    'accent': colors.HexColor('#3B82F6'),       # Bright blue
    'high_risk': colors.HexColor('#DC2626'),    # Red
    'medium_risk': colors.HexColor('#F59E0B'),  # Amber
    'low_risk': colors.HexColor('#10B981'),     # Emerald
    'neutral': colors.HexColor('#6B7280'),      # Gray
    'background': colors.HexColor('#F8FAFC'),   # Light gray
    'text': colors.HexColor('#1F2937'),         # Dark gray
    'text_light': colors.HexColor('#6B7280'),   # Medium gray
    'border': colors.HexColor('#E5E7EB'),       # Light border
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


def create_styles():
    """Create custom paragraph styles"""
    from reportlab.lib.styles import StyleSheet1
    
    styles = StyleSheet1()
    # First add base styles manually
    styles.add(ParagraphStyle(
        name='Normal',
        fontSize=10,
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name='Heading1',
        parent=styles['Normal'],
        fontSize=18,
        leading=22,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='Heading2',
        parent=styles['Normal'],
        fontSize=14,
        leading=18,
        spaceBefore=12,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='Heading3',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        spaceBefore=12,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    ))
    
    # Title style
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontSize=28,
        spaceAfter=30,
        textColor=COLORS['primary'],
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    # Subtitle style
    styles.add(ParagraphStyle(
        name='ReportSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=20,
        textColor=COLORS['text_light'],
        alignment=TA_CENTER
    ))
    
    # Section header
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=12,
        textColor=COLORS['primary'],
        fontName='Helvetica-Bold',
        borderPadding=10
    ))
    
    # Subsection header
    styles.add(ParagraphStyle(
        name='SubsectionHeader',
        parent=styles['Heading3'],
        fontSize=13,
        spaceBefore=15,
        spaceAfter=8,
        textColor=COLORS['secondary'],
        fontName='Helvetica-Bold'
    ))
    
    # Body text
    styles.add(ParagraphStyle(
        name='BodyText',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        textColor=COLORS['text'],
        alignment=TA_JUSTIFY,
        leading=14
    ))
    
    # Executive summary
    styles.add(ParagraphStyle(
        name='ExecutiveSummary',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=10,
        textColor=COLORS['text'],
        alignment=TA_JUSTIFY,
        leading=16,
        leftIndent=20,
        rightIndent=20
    ))
    
    # Risk level text
    styles.add(ParagraphStyle(
        name='RiskHigh',
        parent=styles['Normal'],
        fontSize=12,
        textColor=COLORS['high_risk'],
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='RiskMedium',
        parent=styles['Normal'],
        fontSize=12,
        textColor=COLORS['medium_risk'],
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='RiskLow',
        parent=styles['Normal'],
        fontSize=12,
        textColor=COLORS['low_risk'],
        fontName='Helvetica-Bold'
    ))
    
    # Metric value
    styles.add(ParagraphStyle(
        name='MetricValue',
        parent=styles['Normal'],
        fontSize=24,
        fontName='Helvetica-Bold',
        textColor=COLORS['primary'],
        alignment=TA_CENTER
    ))
    
    # Metric label
    styles.add(ParagraphStyle(
        name='MetricLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLORS['text_light'],
        alignment=TA_CENTER
    ))
    
    # Recommendation item
    styles.add(ParagraphStyle(
        name='Recommendation',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        textColor=COLORS['text'],
        leftIndent=20,
        bulletIndent=10,
        leading=14
    ))
    
    # Footer
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=COLORS['text_light'],
        alignment=TA_CENTER
    ))
    
    return styles


def create_header_footer(canvas, doc, report_title: str, generated_at: str):
    """Add header and footer to each page"""
    canvas.saveState()
    
    # Header line
    canvas.setStrokeColor(COLORS['border'])
    canvas.setLineWidth(0.5)
    canvas.line(50, letter[1] - 40, letter[0] - 50, letter[1] - 40)
    
    # Header text
    canvas.setFont('Helvetica-Bold', 9)
    canvas.setFillColor(COLORS['primary'])
    canvas.drawString(50, letter[1] - 30, "DELIVERY RISK RADAR")
    
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(COLORS['text_light'])
    canvas.drawRightString(letter[0] - 50, letter[1] - 30, report_title)
    
    # Footer
    canvas.setStrokeColor(COLORS['border'])
    canvas.line(50, 40, letter[0] - 50, 40)
    
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(COLORS['text_light'])
    canvas.drawString(50, 25, f"Generated: {generated_at}")
    canvas.drawCentredString(letter[0] / 2, 25, "CONFIDENTIAL - FOR INTERNAL USE ONLY")
    canvas.drawRightString(letter[0] - 50, 25, f"Page {doc.page}")
    
    canvas.restoreState()


def create_risk_distribution_chart(stats: Dict) -> Drawing:
    """Create a pie chart showing risk distribution"""
    drawing = Drawing(300, 180)
    
    risk_dist = stats.get('risk_distribution', {})
    data = [
        risk_dist.get('high', 0),
        risk_dist.get('medium', 0),
        risk_dist.get('low', 0),
        risk_dist.get('neutral', 0)
    ]
    
    # Only show if there's data
    if sum(data) == 0:
        data = [1]  # Placeholder
    
    pie = Pie()
    pie.x = 80
    pie.y = 20
    pie.width = 120
    pie.height = 120
    pie.data = data
    pie.labels = ['High Risk', 'Medium Risk', 'Low Risk', 'Not Analyzed']
    
    pie.slices[0].fillColor = COLORS['high_risk']
    pie.slices[1].fillColor = COLORS['medium_risk']
    pie.slices[2].fillColor = COLORS['low_risk']
    if len(pie.slices) > 3:
        pie.slices[3].fillColor = COLORS['neutral']
    
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white
    
    drawing.add(pie)
    
    # Legend
    legend_x = 220
    legend_y = 130
    labels = [('High Risk', COLORS['high_risk']), 
              ('Medium Risk', COLORS['medium_risk']),
              ('Low Risk', COLORS['low_risk']),
              ('Not Analyzed', COLORS['neutral'])]
    
    for i, (label, color) in enumerate(labels):
        y = legend_y - (i * 25)
        rect = Rect(legend_x, y, 12, 12)
        rect.fillColor = color
        rect.strokeWidth = 0
        drawing.add(rect)
        drawing.add(String(legend_x + 18, y + 2, label, fontSize=9, fillColor=COLORS['text']))
    
    return drawing


def create_metric_box(value: str, label: str, color: colors.Color = None) -> Table:
    """Create a styled metric box"""
    styles = create_styles()
    
    value_style = ParagraphStyle(
        'MetricBoxValue',
        fontSize=28,
        fontName='Helvetica-Bold',
        textColor=color or COLORS['primary'],
        alignment=TA_CENTER
    )
    
    label_style = ParagraphStyle(
        'MetricBoxLabel',
        fontSize=9,
        textColor=COLORS['text_light'],
        alignment=TA_CENTER
    )
    
    data = [[Paragraph(str(value), value_style)], [Paragraph(label, label_style)]]
    
    table = Table(data, colWidths=[1.3*inch])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, COLORS['border']),
        ('BACKGROUND', (0, 0), (-1, -1), COLORS['background']),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    return table


def generate_executive_report(
    projects: List[Dict],
    assessments: List[Dict],
    stats: Dict,
    organization_name: str = "Organization"
) -> bytes:
    """
    Generate a comprehensive executive PDF report
    
    Args:
        projects: List of project data
        assessments: List of latest risk assessments
        stats: Dashboard statistics
        organization_name: Name of the organization
    
    Returns:
        PDF file as bytes
    """
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=60,
        bottomMargin=60
    )
    
    styles = create_styles()
    story = []
    generated_at = datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')
    report_date = datetime.now(timezone.utc).strftime('%B %Y')
    
    # ==================== COVER PAGE ====================
    story.append(Spacer(1, 1.5*inch))
    
    # Logo placeholder (you could add an actual logo here)
    story.append(Paragraph("DELIVERY RISK RADAR", styles['ReportTitle']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Executive Risk Assessment Report", styles['ReportSubtitle']))
    story.append(Spacer(1, 0.5*inch))
    
    # Report period
    cover_info = f"""
    <para align="center">
    <font size="12" color="#1E3A5F"><b>{organization_name}</b></font><br/><br/>
    <font size="11" color="#6B7280">Report Period: {report_date}</font><br/>
    <font size="10" color="#6B7280">Generated: {generated_at}</font>
    </para>
    """
    story.append(Paragraph(cover_info, styles['Normal']))
    
    story.append(Spacer(1, 1.5*inch))
    
    # Classification notice
    classification = """
    <para align="center">
    <font size="9" color="#DC2626"><b>CONFIDENTIAL</b></font><br/>
    <font size="8" color="#6B7280">This document contains sensitive business information intended for executive leadership only.</font>
    </para>
    """
    story.append(Paragraph(classification, styles['Normal']))
    
    story.append(PageBreak())
    
    # ==================== EXECUTIVE SUMMARY ====================
    story.append(Paragraph("1. Executive Summary", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
    
    # Key metrics row
    total_projects = stats.get('total_projects', 0)
    high_risk = stats.get('risk_distribution', {}).get('high', 0)
    medium_risk = stats.get('risk_distribution', {}).get('medium', 0)
    low_risk = stats.get('risk_distribution', {}).get('low', 0)
    
    metrics_data = [
        [
            create_metric_box(str(total_projects), "Total Projects"),
            create_metric_box(str(high_risk), "High Risk", COLORS['high_risk']),
            create_metric_box(str(medium_risk), "Medium Risk", COLORS['medium_risk']),
            create_metric_box(str(low_risk), "Low Risk", COLORS['low_risk']),
        ]
    ]
    
    metrics_table = Table(metrics_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    metrics_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Executive summary text
    if high_risk > 0:
        risk_summary = f"""
        <b>Critical Finding:</b> {high_risk} project{'s' if high_risk > 1 else ''} currently classified as HIGH RISK 
        requiring immediate executive attention. These projects show significant delivery risk indicators 
        that could impact timelines, budgets, or quality outcomes if not addressed promptly.
        """
    elif medium_risk > 0:
        risk_summary = f"""
        <b>Assessment Status:</b> No projects are currently in critical condition. However, {medium_risk} 
        project{'s' if medium_risk > 1 else ''} show{'s' if medium_risk == 1 else ''} MEDIUM RISK levels 
        that warrant monitoring and preventive action to avoid escalation.
        """
    else:
        risk_summary = """
        <b>Assessment Status:</b> All monitored projects are operating within acceptable risk parameters. 
        Continue regular monitoring and analysis to maintain delivery health.
        """
    
    story.append(Paragraph(risk_summary, styles['ExecutiveSummary']))
    story.append(Spacer(1, 0.2*inch))
    
    # Risk distribution chart
    story.append(Paragraph("Risk Distribution Overview", styles['SubsectionHeader']))
    chart = create_risk_distribution_chart(stats)
    story.append(chart)
    story.append(Spacer(1, 0.3*inch))
    
    story.append(PageBreak())
    
    # ==================== HIGH RISK PROJECTS ====================
    high_risk_projects = [p for p in projects if (p.get('risk_level') or '').upper() == 'HIGH']
    
    if high_risk_projects:
        story.append(Paragraph("2. Critical Risk Projects - Immediate Attention Required", styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=COLORS['high_risk'], spaceAfter=15))
        
        for project in high_risk_projects:
            # Find matching assessment
            assessment = next((a for a in assessments if a.get('project_id') == project.get('id')), None)
            
            story.append(KeepTogether([
                Paragraph(f"<font color='#DC2626'><b>▶ {project.get('name', 'Unknown Project')}</b></font>", styles['SubsectionHeader']),
                
                # Project info table
                Table([
                    ['Risk Score:', f"{project.get('risk_score', 0)}%", 'Team Lead:', project.get('team_lead', 'N/A')],
                    ['Team Size:', str(project.get('team_size', 'N/A')), 'Target End:', project.get('target_end_date', 'N/A')],
                ], colWidths=[1.2*inch, 1.8*inch, 1.2*inch, 2*inch], style=TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('TEXTCOLOR', (0, 0), (-1, -1), COLORS['text']),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ])),
                Spacer(1, 0.1*inch),
            ]))
            
            if assessment:
                # AI Analysis narrative
                if assessment.get('narrative'):
                    story.append(Paragraph("<b>AI Risk Analysis:</b>", styles['BodyText']))
                    story.append(Paragraph(assessment['narrative'], styles['BodyText']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Risk drivers
                if assessment.get('risk_drivers'):
                    story.append(Paragraph("<b>Key Risk Drivers:</b>", styles['BodyText']))
                    for driver in assessment['risk_drivers'][:3]:
                        driver_text = f"• <b>{driver.get('name', 'Unknown')}</b> ({driver.get('severity', 'N/A')} severity): {driver.get('description', '')}"
                        story.append(Paragraph(driver_text, styles['Recommendation']))
                    story.append(Spacer(1, 0.1*inch))
                
                # Impact prediction
                if assessment.get('impact_prediction'):
                    impact = assessment['impact_prediction']
                    story.append(Paragraph("<b>Projected Impact:</b>", styles['BodyText']))
                    impact_data = [
                        ['Timeline Impact', 'Cost Impact', 'Quality Impact'],
                        [
                            impact.get('timeline_impact', 'Unknown'),
                            impact.get('cost_impact', 'Unknown'),
                            impact.get('quality_impact', 'Unknown')
                        ]
                    ]
                    impact_table = Table(impact_data, colWidths=[2*inch, 2*inch, 2*inch])
                    impact_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BACKGROUND', (0, 0), (-1, 0), COLORS['background']),
                        ('TEXTCOLOR', (0, 0), (-1, -1), COLORS['text']),
                        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('TOPPADDING', (0, 0), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    story.append(impact_table)
                    story.append(Spacer(1, 0.1*inch))
                
                # Recommendations
                if assessment.get('recommendations'):
                    story.append(Paragraph("<b>Recommended Actions:</b>", styles['BodyText']))
                    for i, rec in enumerate(assessment['recommendations'][:5], 1):
                        story.append(Paragraph(f"{i}. {rec}", styles['Recommendation']))
            
            story.append(Spacer(1, 0.3*inch))
            story.append(HRFlowable(width="100%", thickness=0.5, color=COLORS['border'], spaceAfter=15))
        
        story.append(PageBreak())
    
    # ==================== ALL PROJECTS SUMMARY ====================
    story.append(Paragraph("3. Complete Project Portfolio Risk Summary", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
    
    # Projects table
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
        
        # Dynamic row coloring based on risk
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
        
        # Color code risk level cells
        for i, row in enumerate(table_data[1:], 1):
            risk = row[1].upper() if row[1] else ''
            if risk == 'HIGH':
                table_style.append(('TEXTCOLOR', (1, i), (1, i), COLORS['high_risk']))
                table_style.append(('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'))
            elif risk == 'MEDIUM':
                table_style.append(('TEXTCOLOR', (1, i), (1, i), COLORS['medium_risk']))
                table_style.append(('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'))
            elif risk == 'LOW':
                table_style.append(('TEXTCOLOR', (1, i), (1, i), COLORS['low_risk']))
        
        projects_table.setStyle(TableStyle(table_style))
        story.append(projects_table)
    else:
        story.append(Paragraph("No projects found in the system.", styles['BodyText']))
    
    story.append(Spacer(1, 0.5*inch))
    
    # ==================== RISK DIMENSIONS ANALYSIS ====================
    if assessments:
        story.append(PageBreak())
        story.append(Paragraph("4. Enterprise Risk Dimensions Analysis", styles['SectionHeader']))
        story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
        
        # Aggregate risk dimensions across all assessments
        dimensions = {
            'Scope Creep': [],
            'Dependency Failure': [],
            'False Reporting': [],
            'Quality Collapse': [],
            'Team Burnout': [],
            'Vendor Risk': []
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
        
        # Calculate averages
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
        
        story.append(Spacer(1, 0.3*inch))
        
        # Dimension descriptions
        story.append(Paragraph("<b>Risk Dimension Definitions:</b>", styles['BodyText']))
        dim_descriptions = [
            "<b>Scope Creep:</b> Uncontrolled changes or continuous growth in project scope",
            "<b>Dependency Failure:</b> Risks from external teams, vendors, or system dependencies",
            "<b>False Reporting:</b> Discrepancy between reported status and actual delivery health",
            "<b>Quality Collapse:</b> Increasing defects, technical debt, or stability issues",
            "<b>Team Burnout:</b> Overcommitment, unsustainable workload, or resource strain",
            "<b>Vendor Risk:</b> External partner performance, SLA adherence, or contract issues"
        ]
        for desc in dim_descriptions:
            story.append(Paragraph(f"• {desc}", styles['Recommendation']))
    
    # ==================== RECOMMENDATIONS ====================
    story.append(PageBreak())
    story.append(Paragraph("5. Strategic Recommendations", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1, color=COLORS['border'], spaceAfter=15))
    
    # Collect unique recommendations from all high/medium risk assessments
    all_recommendations = []
    for assessment in assessments:
        project = next((p for p in projects if p.get('id') == assessment.get('project_id')), {})
        if (project.get('risk_level') or '').upper() in ['HIGH', 'MEDIUM']:
            for rec in assessment.get('recommendations', []):
                if rec not in all_recommendations:
                    all_recommendations.append(rec)
    
    if all_recommendations:
        story.append(Paragraph("<b>Priority Actions for Leadership:</b>", styles['BodyText']))
        story.append(Spacer(1, 0.1*inch))
        
        for i, rec in enumerate(all_recommendations[:10], 1):
            story.append(Paragraph(f"<b>{i}.</b> {rec}", styles['Recommendation']))
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
    
    This report utilizes AI-powered analysis (GPT-5.2) to evaluate delivery risk across six dimensions. 
    Risk scores are calculated using a weighted combination of:<br/><br/>
    
    • <b>Execution Signals:</b> Sprint velocity, backlog churn, blocked tickets, carry-over rates<br/>
    • <b>Communication Patterns:</b> Escalation frequency, decision pending threads, sentiment analysis<br/>
    • <b>Quality Indicators:</b> Defect rates, regression frequency, release stability<br/>
    • <b>Resource Metrics:</b> Team capacity, overtime patterns, turnover risk<br/>
    • <b>Governance Compliance:</b> Status report accuracy, risk mitigation tracking<br/><br/>
    
    <b>Risk Level Classification:</b><br/>
    • HIGH (70-100%): Immediate intervention required<br/>
    • MEDIUM (40-69%): Active monitoring and preventive action needed<br/>
    • LOW (0-39%): Standard monitoring, no immediate concerns<br/><br/>
    
    <b>Confidence Score:</b> Indicates data completeness and analysis reliability. 
    Higher scores reflect more comprehensive data sources.
    """
    story.append(Paragraph(methodology, styles['BodyText']))
    
    # Build PDF
    def first_page(canvas, doc):
        pass  # Cover page has no header/footer
    
    def later_pages(canvas, doc):
        create_header_footer(canvas, doc, "Executive Risk Report", generated_at)
    
    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages)
    
    buffer.seek(0)
    return buffer.getvalue()
