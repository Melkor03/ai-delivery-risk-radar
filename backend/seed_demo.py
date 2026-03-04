#!/usr/bin/env python3
"""
seed_demo.py — Delivery Risk Radar Demo Data Seeder
====================================================
Populates MongoDB with realistic demo data for showcasing the product.

Usage:
    python seed_demo.py              # Seed (skips if demo user exists)
    python seed_demo.py --reset      # Wipe all data and re-seed fresh

Demo login credentials:
    Email:    demo@riskradar.com
    Password: Demo@1234
"""

import asyncio
import uuid
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME   = os.environ.get("DB_NAME", "risk_radar")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def ts(days_ago=0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()

def uid():
    return str(uuid.uuid4())

# ─────────────────────────────────────────────
# DEMO PROJECTS
# ─────────────────────────────────────────────
PROJECTS = [
    {
        "name": "Phoenix Core Banking Migration",
        "description": "Migrating legacy mainframe to cloud-native microservices. Critical Q2 compliance deadline.",
        "team_lead": "Priya Menon",
        "team_size": 18,
        "start_date": "2025-11-01",
        "target_end_date": "2026-04-30",
        "status": "active",
        "risk_level": "HIGH",
        "risk_score": 82,
    },
    {
        "name": "Customer AI Insights Dashboard",
        "description": "ML-powered dashboard for churn prediction and customer behavior analytics.",
        "team_lead": "Arjun Nair",
        "team_size": 9,
        "start_date": "2026-01-15",
        "target_end_date": "2026-05-31",
        "status": "active",
        "risk_level": "MEDIUM",
        "risk_score": 47,
    },
    {
        "name": "Mobile App v3.0 — React Native Rewrite",
        "description": "Full rewrite with offline-first architecture and redesigned UX.",
        "team_lead": "Kavitha Rao",
        "team_size": 12,
        "start_date": "2025-12-01",
        "target_end_date": "2026-06-15",
        "status": "active",
        "risk_level": "MEDIUM",
        "risk_score": 58,
    },
    {
        "name": "DevOps Infrastructure Modernisation",
        "description": "Kubernetes migration, CI/CD rebuild, full observability stack.",
        "team_lead": "Sanjay Kumar",
        "team_size": 6,
        "start_date": "2026-01-01",
        "target_end_date": "2026-07-31",
        "status": "active",
        "risk_level": "LOW",
        "risk_score": 23,
    },
    {
        "name": "UPI 2.0 Payment Gateway Integration",
        "description": "UPI mandate management and recurring payments for B2B enterprise clients.",
        "team_lead": "Deepa Sharma",
        "team_size": 7,
        "start_date": "2026-02-01",
        "target_end_date": "2026-05-15",
        "status": "active",
        "risk_level": "HIGH",
        "risk_score": 76,
    },
]

# ─────────────────────────────────────────────
# RISK ASSESSMENTS (one per project)
# ─────────────────────────────────────────────
ASSESSMENTS = [
    {   # Phoenix — HIGH
        "risk_level": "HIGH", "risk_score": 82, "confidence": 91,
        "risk_drivers": [
            {"name": "Scope Creep — Requirements Drift", "severity": "high",
             "description": "32 new requirements added post-Sprint 4. Backlog grown 40% since kick-off."},
            {"name": "Dependency Failure — Vendor Delays", "severity": "high",
             "description": "Core middleware vendor 3 weeks behind on API delivery, blocking 6 downstream tasks."},
            {"name": "Team Burnout Risk", "severity": "medium",
             "description": "Average cycle time up 62% over last 4 sprints. 3 members logging 60+ hour weeks."},
        ],
        "impact_prediction": {
            "timeline_impact": "High probability of 6–10 week delay beyond April deadline",
            "cost_impact": "Estimated ₹45–80L cost overrun if delays compound into Q3",
            "quality_impact": "Regression test coverage falling — 3 P1 bugs in last sprint release"
        },
        "recommendations": [
            "Immediately freeze scope for next 2 sprints — no new requirements",
            "Escalate vendor dependency to CTO level with contractual SLA enforcement",
            "Redistribute workload — move 2 backend engineers from Mobile App team temporarily",
            "Daily 15-min blocker standups with team leads until critical path is clear",
            "Commission independent QA audit of current test coverage",
        ],
        "narrative": "Phoenix Core Banking Migration is the highest-risk project in the portfolio. The combination of uncontrolled scope expansion, a critical vendor bottleneck, and early burnout signals creates a compounding risk pattern that historically precedes project failure. The 40% backlog growth since Sprint 4 suggests requirements governance has broken down — this is the most urgent corrective action needed. The vendor delay on middleware APIs is currently the critical path blocker; escalation to contractual SLA enforcement is non-negotiable if the April compliance deadline is to be met. Team burnout metrics are a lagging indicator — act on them now before attrition becomes a factor in Q2.",
        "risk_dimensions": {"scope_creep": 88, "dependency_failure": 85, "false_reporting": 45, "quality_collapse": 72, "burnout": 78, "vendor_risk": 82},
    },
    {   # AI Dashboard — MEDIUM
        "risk_level": "MEDIUM", "risk_score": 47, "confidence": 84,
        "risk_drivers": [
            {"name": "ML Model Performance", "severity": "medium",
             "description": "Churn prediction model at 71% accuracy — target is 85%. Still 3 iterations away."},
            {"name": "Data Pipeline Instability", "severity": "medium",
             "description": "ETL pipeline failing 2–3 times per week in staging, causing dashboard stale data."},
        ],
        "impact_prediction": {
            "timeline_impact": "2–3 week delay likely if ML accuracy targets aren't met by Sprint 8",
            "cost_impact": "Within budget — cloud compute overage of ~₹3L if model retraining extends",
            "quality_impact": "Dashboard may launch with reduced feature set if pipeline issues persist"
        },
        "recommendations": [
            "Schedule model performance review with data science lead — set hard accuracy gate",
            "Assign dedicated DevOps engineer to stabilise ETL pipeline before Sprint 7",
            "Define MVP scope clearly — launch core analytics first, add ML predictions in v1.1",
        ],
        "narrative": "The Customer AI Insights Dashboard is in a manageable risk position but requires focused attention on two technical quality gates. ML model accuracy at 71% is below the 85% product requirement — this is a known risk the team is actively working, but it needs a firm decision point: either hit the accuracy target by Sprint 8 or redefine scope to launch without the churn prediction feature. The ETL instability is operationally concerning and should be fixed as a P0 before any further feature development.",
        "risk_dimensions": {"scope_creep": 30, "dependency_failure": 42, "false_reporting": 20, "quality_collapse": 55, "burnout": 38, "vendor_risk": 25},
    },
    {   # Mobile App — MEDIUM
        "risk_level": "MEDIUM", "risk_score": 58, "confidence": 78,
        "risk_drivers": [
            {"name": "React Native Performance Issues", "severity": "medium",
             "description": "App startup time 4.2s on mid-range Android — target is under 2s. Architecture rethink needed."},
            {"name": "Design-Dev Misalignment", "severity": "medium",
             "description": "5 screens rejected by design in last sprint review. Rework adding 2-3 days per sprint."},
            {"name": "Third-Party SDK Compatibility", "severity": "low",
             "description": "Payment SDK incompatible with RN 0.73. Workaround found but adds tech debt."},
        ],
        "impact_prediction": {
            "timeline_impact": "3–4 week delay if performance issues aren't resolved by Sprint 9",
            "cost_impact": "Design rework adding ~15% effort overhead per sprint",
            "quality_impact": "Performance on low-end devices remains a launch blocker"
        },
        "recommendations": [
            "Performance spike: dedicate 1 sprint to profiling and optimisation before new features",
            "Mandatory design review at component level — not just full-screen review at sprint end",
            "Evaluate upgrade to React Native 0.74 to resolve SDK compatibility cleanly",
        ],
        "narrative": "The Mobile App rewrite is trending towards a medium-risk delay driven by technical quality debt accumulating faster than it is being resolved. The 4.2s startup time on Android mid-range devices is a hard launch blocker — this needs a dedicated performance sprint now, not after feature completion. The design-dev cycle mismatch is a process problem that a simple mid-sprint design checkpoint would resolve immediately.",
        "risk_dimensions": {"scope_creep": 45, "dependency_failure": 35, "false_reporting": 28, "quality_collapse": 68, "burnout": 42, "vendor_risk": 55},
    },
    {   # DevOps — LOW
        "risk_level": "LOW", "risk_score": 23, "confidence": 89,
        "risk_drivers": [
            {"name": "Knowledge Concentration", "severity": "low",
             "description": "Single engineer owns Kubernetes config. Bus factor of 1 is a project risk."},
        ],
        "impact_prediction": {
            "timeline_impact": "On track — no delays anticipated",
            "cost_impact": "Within budget with 15% contingency remaining",
            "quality_impact": "High — documentation and runbooks being produced proactively"
        },
        "recommendations": [
            "Cross-train at least one more engineer on Kubernetes configuration",
            "Schedule infrastructure chaos engineering test before going live",
        ],
        "narrative": "DevOps Infrastructure Modernisation is the healthiest project in the portfolio. The team is executing methodically with strong documentation practices. The only notable risk is knowledge concentration in the Kubernetes domain — a single bus-factor that should be mitigated through cross-training before the project enters production.",
        "risk_dimensions": {"scope_creep": 12, "dependency_failure": 18, "false_reporting": 10, "quality_collapse": 22, "burnout": 20, "vendor_risk": 15},
    },
    {   # UPI — HIGH
        "risk_level": "HIGH", "risk_score": 76, "confidence": 87,
        "risk_drivers": [
            {"name": "RBI Regulatory Compliance Gap", "severity": "high",
             "description": "3 mandatory RBI compliance controls not yet implemented. Audit deadline is April 15."},
            {"name": "NPCI API Instability", "severity": "high",
             "description": "NPCI sandbox returning intermittent 503s — blocking end-to-end testing for 8 days."},
            {"name": "Scope Addition — Mandate Management", "severity": "medium",
             "description": "Mandate management feature added mid-sprint, not in original scope. Adding 3 weeks."},
        ],
        "impact_prediction": {
            "timeline_impact": "May 15 deadline at serious risk — likely slip to June without scope cut",
            "cost_impact": "Regulatory non-compliance penalty risk dwarfs project cost",
            "quality_impact": "Cannot go live until all RBI compliance controls are verified"
        },
        "recommendations": [
            "Make RBI compliance controls the only Sprint 6 priority — nothing else ships",
            "Escalate NPCI API instability to account manager and request dedicated sandbox environment",
            "Descope mandate management to v1.1 — protect the core payment flow and compliance deadline",
            "Engage a BFSI compliance consultant for an independent review before April 15 audit",
        ],
        "narrative": "The UPI 2.0 integration carries the second-highest risk in the portfolio, primarily driven by regulatory compliance gaps that carry financial penalty risk far exceeding the project budget. The RBI compliance deadline of April 15 is non-negotiable — everything else must be subordinated to meeting it. The NPCI sandbox instability is an external blocker requiring active vendor escalation. Recommending immediate scope reduction to protect the compliance timeline.",
        "risk_dimensions": {"scope_creep": 62, "dependency_failure": 78, "false_reporting": 35, "quality_collapse": 58, "burnout": 52, "vendor_risk": 88},
    },
]

# ─────────────────────────────────────────────
# MANUAL ENTRIES (status reports per project)
# ─────────────────────────────────────────────
ENTRIES = [
    # Phoenix
    ("Phoenix Core Banking Migration", "status_report", "Sprint 6 Status Update",
     "Sprint 6 is 65% complete. 8 of 12 stories delivered. 4 stories blocked pending vendor API. Team working extended hours — flagging burnout risk. Scope additions from business team this week: 3 new compliance screens requested urgently.", 5),
    ("Phoenix Core Banking Migration", "meeting_notes", "Risk Review — CTO Meeting",
     "CTO flagged April deadline as critical. Discussed vendor delays — legal team reviewing SLA clauses. Decision: freeze all non-regulatory scope until vendor delivers. Team morale discussed — HR to check in with leads.", 10),
    # AI Dashboard
    ("Customer AI Insights Dashboard", "status_report", "Sprint 5 Status Update",
     "Model accuracy improved from 68% to 71% this sprint. Target remains 85%. ETL pipeline had 2 failures this week — investigating root cause. On track for UI delivery, ML features may slip by 1 sprint.", 3),
    # Mobile App
    ("Mobile App v3.0 — React Native Rewrite", "status_report", "Sprint 7 Status Update",
     "Performance profiling complete — root cause identified as unoptimised image loading in feed screen. Fix estimated 4 days. Design rejected 5 screens — rework in progress. SDK compatibility workaround merged.", 2),
    # UPI
    ("UPI 2.0 Payment Gateway Integration", "status_report", "Compliance Readiness Review",
     "URGENT: RBI audit on April 15. 3 compliance controls still open: transaction log immutability, dispute resolution API, fraud detection hooks. NPCI sandbox has been unstable for 8 days — raised ticket. Risk: we cannot do end-to-end testing.", 1),
]

# ─────────────────────────────────────────────
# MAIN SEEDER
# ─────────────────────────────────────────────
async def seed(reset=False):
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    if reset:
        print("🗑️  Resetting database...")
        for col in ["users", "projects", "risk_assessments", "manual_entries",
                    "notifications", "risk_snapshots"]:
            await db[col].drop()
        print("   Done.\n")

    # Check if already seeded
    existing = await db.users.find_one({"email": "demo@riskradar.com"})
    if existing and not reset:
        print("⚠️  Demo data already exists. Run with --reset to re-seed.")
        client.close()
        return

    print("🌱 Seeding demo data...\n")

    # ── Demo user ──
    user_id = uid()
    await db.users.insert_one({
        "id": user_id,
        "email": "demo@riskradar.com",
        "password": pwd_context.hash("Demo@1234"),
        "name": "Suresh J",
        "role": "admin",
        "created_at": ts(30),
    })
    print("✅ Demo user created")
    print("   Email:    demo@riskradar.com")
    print("   Password: Demo@1234\n")

    # ── Projects + Assessments ──
    project_ids = {}
    for i, proj in enumerate(PROJECTS):
        pid = uid()
        project_ids[proj["name"]] = pid
        last_analyzed = ts(1) if proj["risk_level"] != "LOW" else ts(3)

        await db.projects.insert_one({
            "id": pid,
            "name": proj["name"],
            "description": proj["description"],
            "team_lead": proj["team_lead"],
            "team_size": proj["team_size"],
            "start_date": proj["start_date"],
            "target_end_date": proj["target_end_date"],
            "status": proj["status"],
            "risk_level": proj["risk_level"],
            "risk_score": proj["risk_score"],
            "last_analyzed": last_analyzed,
            "created_at": ts(30),
            "created_by": user_id,
        })

        # Assessment
        a = ASSESSMENTS[i]
        assessment_id = uid()
        await db.risk_assessments.insert_one({
            "id": assessment_id,
            "project_id": pid,
            "risk_level": a["risk_level"],
            "risk_score": a["risk_score"],
            "confidence": a["confidence"],
            "risk_drivers": a["risk_drivers"],
            "impact_prediction": a["impact_prediction"],
            "recommendations": a["recommendations"],
            "narrative": a["narrative"],
            "risk_dimensions": a["risk_dimensions"],
            "created_at": last_analyzed,
        })

        # Historical snapshots (last 7 days) for trend chart
        for day in range(7, 0, -1):
            variance = (day % 3) - 1  # small fluctuation
            await db.risk_snapshots.insert_one({
                "id": uid(),
                "project_id": pid,
                "risk_score": max(0, min(100, proj["risk_score"] + variance * 3)),
                "risk_level": proj["risk_level"],
                "risk_dimensions": {k: max(0, min(100, v + variance * 2))
                                    for k, v in a["risk_dimensions"].items()},
                "snapshot_date": ts(day)[:10],
                "created_at": ts(day),
            })

        print(f"   ✅ {proj['name']} [{proj['risk_level']}]")

    # ── Manual entries ──
    print("\n✅ Seeding manual entries...")
    for (proj_name, etype, title, content, days) in ENTRIES:
        pid = project_ids.get(proj_name)
        if pid:
            await db.manual_entries.insert_one({
                "id": uid(),
                "project_id": pid,
                "entry_type": etype,
                "title": title,
                "content": content,
                "date": ts(days)[:10],
                "created_by": user_id,
                "created_at": ts(days),
            })

    # ── Welcome notifications ──
    notifs = [
        ("🔴 HIGH RISK: Phoenix Core Banking Migration",
         "Risk score 82/100 — vendor delays and scope creep detected", "alert",
         project_ids["Phoenix Core Banking Migration"]),
        ("🟡 MEDIUM RISK: Mobile App v3.0 trending upward",
         "Risk increased from 45 → 58 over last 7 days", "warning",
         project_ids["Mobile App v3.0 — React Native Rewrite"]),
        ("🔴 HIGH RISK: UPI compliance deadline approaching",
         "3 RBI compliance controls open — April 15 audit at risk", "alert",
         project_ids["UPI 2.0 Payment Gateway Integration"]),
        ("✅ Welcome to Delivery Risk Radar",
         "Demo environment loaded. Explore the 5 sample projects to see AI risk analysis in action.", "info", None),
    ]
    for title, msg, ntype, pid in notifs:
        await db.notifications.insert_one({
            "id": uid(),
            "user_id": user_id,
            "title": title,
            "message": msg,
            "type": ntype,
            "project_id": pid,
            "read": False,
            "created_at": ts(0),
        })

    client.close()

    print("\n" + "="*50)
    print("🎉 Demo data seeded successfully!")
    print("="*50)
    print(f"\n  Projects:    {len(PROJECTS)}")
    print(f"  Assessments: {len(ASSESSMENTS)}")
    print(f"  Entries:     {len(ENTRIES)}")
    print(f"  Snapshots:   {len(PROJECTS) * 7} (7 days each)")
    print(f"  Notifs:      {len(notifs)}")
    print("\n  Login at: http://localhost:3000")
    print("  Email:    demo@riskradar.com")
    print("  Password: Demo@1234")
    print("="*50 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data for Delivery Risk Radar")
    parser.add_argument("--reset", action="store_true", help="Wipe all data and re-seed")
    args = parser.parse_args()
    asyncio.run(seed(reset=args.reset))
