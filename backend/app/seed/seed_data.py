import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.core.clock import get_clock
from app.core.security import get_password_hash
from app.models.entities import (
    User, Team, Account, Deal, Conversation, EvidenceExcerpt,
    ConversationFinding, Activity, RiskAssessment, RiskSignal,
    RiskConfig, Alert, RoutingRule, RoutingDecision, FollowUpAction,
    FieldProvenance, AuditEvent
)
from app.services.extractor import extract_evidence_and_findings
from app.services.risk_engine import assess_deal_risk, DEFAULT_RISK_CONFIG
from app.services.routing_engine import evaluate_routing
from app.services.action_service import generate_deduped_actions_for_deal

def seed_database(db: Session) -> Dict[str, int]:
    """
    Idempotent database seeder.
    Populates rich, internally consistent synthetic dataset.
    """
    clock = get_clock()
    now = clock.now()

    # Check if already seeded
    existing_user_count = db.query(User).count()
    if existing_user_count >= 8:
        return {"status": "already_seeded", "users": existing_user_count}

    # 1. Teams
    teams_data = [
        {"name": "Commercial & Pricing Solutions", "responsibilities": ["pricing", "commercials", "negotiation"]},
        {"name": "Renewals & Account Growth", "responsibilities": ["renewals", "expansion", "retention"]},
        {"name": "Technical Solutions & Architecture", "responsibilities": ["technical", "security", "implementation", "architecture"]}
    ]
    teams = {}
    for t_data in teams_data:
        team = db.query(Team).filter(Team.name == t_data["name"]).first()
        if not team:
            team = Team(name=t_data["name"], responsibilities=t_data["responsibilities"])
            db.add(team)
            db.flush()
        teams[team.name] = team

    # 2. Users
    pwd_hash = get_password_hash("DemoSecret123!")
    users_data = [
        {"email": "alex.morgan@revpilot.local", "name": "Alex Morgan (Manager)", "role": "manager", "team": "Commercial & Pricing Solutions"},
        {"email": "marcus.vance@revpilot.local", "name": "Marcus Vance (Pricing Lead)", "role": "rep", "team": "Commercial & Pricing Solutions"},
        {"email": "elena.rostova@revpilot.local", "name": "Elena Rostova (Commercial AE)", "role": "rep", "team": "Commercial & Pricing Solutions"},
        {"email": "sarah.chen@revpilot.local", "name": "Sarah Chen (Renewals Director)", "role": "manager", "team": "Renewals & Account Growth"},
        {"email": "david.kim@revpilot.local", "name": "David Kim (Renewal Specialist)", "role": "rep", "team": "Renewals & Account Growth"},
        {"email": "priya.patel@revpilot.local", "name": "Priya Patel (Solutions Architect)", "role": "rep", "team": "Technical Solutions & Architecture"},
        {"email": "jordan.taylor@revpilot.local", "name": "Jordan Taylor (Implementation Eng)", "role": "rep", "team": "Technical Solutions & Architecture"},
        {"email": "admin@revpilot.local", "name": "System Administrator", "role": "admin", "team": "Commercial & Pricing Solutions"},
        {"email": "demo@revpilot.local", "name": "Demo Evaluator", "role": "demo_evaluator", "team": "Commercial & Pricing Solutions"},
    ]
    users = {}
    for u_data in users_data:
        u = db.query(User).filter(User.email == u_data["email"]).first()
        if not u:
            u = User(
                email=u_data["email"],
                name=u_data["name"],
                role=u_data["role"],
                team_id=teams[u_data["team"]].id,
                password_hash=pwd_hash
            )
            db.add(u)
            db.flush()
        users[u.email] = u

    # 3. Risk Configurations
    for code, cfg in DEFAULT_RISK_CONFIG.items():
        existing_cfg = db.query(RiskConfig).filter(RiskConfig.signal_code == code).first()
        if not existing_cfg:
            db.add(RiskConfig(
                signal_code=code,
                weight=cfg["weight"],
                threshold_params={k: v for k, v in cfg.items() if k not in ["weight", "enabled"]},
                enabled=cfg["enabled"],
                version=1
            ))

    # 4. Routing Rules
    routing_rules_data = [
        {
            "name": "High Urgency Pricing Escalation",
            "priority_order": 1,
            "conditions": {"topic": "pricing", "urgency": "critical"},
            "target_owner_email": "marcus.vance@revpilot.local",
            "target_team": "Commercial & Pricing Solutions",
            "priority_outcome": "critical",
            "specificity": 2
        },
        {
            "name": "Standard Pricing Review",
            "priority_order": 5,
            "conditions": {"topic": "pricing"},
            "target_owner_email": "elena.rostova@revpilot.local",
            "target_team": "Commercial & Pricing Solutions",
            "priority_outcome": "high",
            "specificity": 1
        },
        {
            "name": "Strategic Enterprise Renewal",
            "priority_order": 2,
            "conditions": {"topic": "renewal", "urgency": "high"},
            "target_owner_email": "david.kim@revpilot.local",
            "target_team": "Renewals & Account Growth",
            "priority_outcome": "high",
            "specificity": 2
        },
        {
            "name": "Technical Architecture & Security Review",
            "priority_order": 3,
            "conditions": {"topic": "technical"},
            "target_owner_email": "priya.patel@revpilot.local",
            "target_team": "Technical Solutions & Architecture",
            "priority_outcome": "medium",
            "specificity": 1
        },
        # Ambiguous routing test rules: same priority order and specificity, conflicting owners!
        {
            "name": "Ambiguous Branch Alpha (Conflict Demo)",
            "priority_order": 10,
            "conditions": {"topic": "ambiguous_contract"},
            "target_owner_email": "elena.rostova@revpilot.local",
            "target_team": "Commercial & Pricing Solutions",
            "priority_outcome": "high",
            "specificity": 1
        },
        {
            "name": "Ambiguous Branch Beta (Conflict Demo)",
            "priority_order": 10,
            "conditions": {"topic": "ambiguous_contract"},
            "target_owner_email": "david.kim@revpilot.local",
            "target_team": "Renewals & Account Growth",
            "priority_outcome": "high",
            "specificity": 1
        }
    ]

    for rr in routing_rules_data:
        existing_r = db.query(RoutingRule).filter(RoutingRule.name == rr["name"]).first()
        if not existing_r:
            db.add(RoutingRule(
                name=rr["name"],
                priority_order=rr["priority_order"],
                conditions=rr["conditions"],
                target_owner_user_id=users[rr["target_owner_email"]].id,
                target_team_id=teams[rr["target_team"]].id,
                priority_outcome=rr["priority_outcome"],
                enabled=True,
                specificity=rr["specificity"]
            ))

    db.flush()

    # 5. Accounts (~12 Synthetic Enterprise Accounts)
    accounts_data = [
        {"name": "Northwind Logistics Demo", "industry": "Logistics & Supply Chain", "owner": "elena.rostova@revpilot.local"},
        {"name": "Apex Global BioTech", "industry": "Pharmaceuticals", "owner": "marcus.vance@revpilot.local"},
        {"name": "Acme Precision Cloud", "industry": "Enterprise Software", "owner": "elena.rostova@revpilot.local"},
        {"name": "Vanguard Financial Services", "industry": "Banking & Fintech", "owner": "david.kim@revpilot.local"},
        {"name": "Starlight Health Network", "industry": "Healthcare", "owner": "david.kim@revpilot.local"},
        {"name": "CyberShield Defense", "industry": "Cybersecurity", "owner": "priya.patel@revpilot.local"},
        {"name": "Nexus Retail Systems", "industry": "Omnichannel Retail", "owner": "elena.rostova@revpilot.local"},
        {"name": "Zephyr Green Energy", "industry": "CleanTech", "owner": "marcus.vance@revpilot.local"},
        {"name": "OmniCorp Manufacturing", "industry": "Industrial IoT", "owner": "jordan.taylor@revpilot.local"},
        {"name": "Horizon Media Group", "industry": "Digital Media", "owner": "david.kim@revpilot.local"},
        {"name": "Atlas Cloud Infrastructure", "industry": "Telecom & Cloud", "owner": "priya.patel@revpilot.local"},
        {"name": "Beacon Freight Solutions", "industry": "Freight & Maritime", "owner": "elena.rostova@revpilot.local"},
    ]
    accounts = {}
    for a_data in accounts_data:
        norm = a_data["name"].strip().lower()
        acc = db.query(Account).filter(Account.normalized_name == norm).first()
        if not acc:
            acc = Account(
                name=a_data["name"],
                normalized_name=norm,
                industry=a_data["industry"],
                owner_user_id=users[a_data["owner"]].id,
                synthetic_flag=True
            )
            db.add(acc)
            db.flush()
        accounts[acc.name] = acc

    # 6. Deals (~20 Synthetic Deals with Designed Scenarios)
    deals_data = [
        # Scenario 1: High-value deal with unresolved pricing objection AND no customer reply > 14 days (DL-1001) -> High/Critical
        {
            "deal_code": "DL-1001", "name": "Global Fleet Intelligence Expansion", "account": "Northwind Logistics Demo",
            "value": 240000.0, "stage": "Negotiation", "status": "open", "owner": "marcus.vance@revpilot.local",
            "close_days": 18, "tracks_next": True, "dm_known": True, "next_step_days": None,
            "last_act_days": 21
        },
        # Scenario 2: Stalled deal with repeated postponements & no next step (DL-1002)
        {
            "deal_code": "DL-1002", "name": "Clinical Trial Workflow Automation", "account": "Apex Global BioTech",
            "value": 175000.0, "stage": "Proposal", "status": "open", "owner": "elena.rostova@revpilot.local",
            "close_days": 45, "tracks_next": True, "dm_known": False, "next_step_days": None,
            "last_act_days": 18
        },
        # Scenario 3: Healthy deal (recent replies, clear next step, no objections) -> Low (DL-1003)
        {
            "deal_code": "DL-1003", "name": "Enterprise Telemetry Infrastructure", "account": "Acme Precision Cloud",
            "value": 110000.0, "stage": "Proposal", "status": "open", "owner": "elena.rostova@revpilot.local",
            "close_days": 35, "tracks_next": True, "dm_known": True, "next_step_days": 3,
            "last_act_days": 2
        },
        # Scenario 4: Medium risk deal with single product concern (DL-1004)
        {
            "deal_code": "DL-1004", "name": "Securities Data Compliance Suite", "account": "Vanguard Financial Services",
            "value": 85000.0, "stage": "Discovery", "status": "open", "owner": "priya.patel@revpilot.local",
            "close_days": 60, "tracks_next": True, "dm_known": True, "next_step_days": 7,
            "last_act_days": 4
        },
        # Scenario 5: Deal with manually corrected field & provenance (DL-1005)
        {
            "deal_code": "DL-1005", "name": "Hospital Network EHR Bridge", "account": "Starlight Health Network",
            "value": 195000.0, "stage": "Negotiation", "status": "open", "owner": "david.kim@revpilot.local",
            "close_days": 20, "tracks_next": True, "dm_known": True, "next_step_days": 5,
            "last_act_days": 3, "manual_override": {"field": "stage", "val": "Negotiation", "source_val": "Proposal"}
        },
        # Scenario 6: Urgent renewal with approaching deadline (DL-1006)
        {
            "deal_code": "DL-1006", "name": "Zero-Trust Perimeter Annual Renewal", "account": "CyberShield Defense",
            "value": 310000.0, "stage": "Legal/Review", "status": "open", "owner": "sarah.chen@revpilot.local",
            "close_days": 12, "renewal_days": 12, "tracks_next": True, "dm_known": True, "next_step_days": None,
            "last_act_days": 15
        },
        # Scenario 7: Next-step data is UNKNOWN (tracks_next_steps = False) -> tests unknown != risk (DL-1007)
        {
            "deal_code": "DL-1007", "name": "Store Inventory Tracking POC", "account": "Nexus Retail Systems",
            "value": 45000.0, "stage": "Discovery", "status": "open", "owner": "elena.rostova@revpilot.local",
            "close_days": 50, "tracks_next": False, "dm_known": None, "next_step_days": None,
            "last_act_days": 6
        },
        # Additional Deals (DL-1008 to DL-1020)
        {"deal_code": "DL-1008", "name": "Grid Optimization Phase 2", "account": "Zephyr Green Energy", "value": 130000.0, "stage": "Proposal", "status": "open", "owner": "marcus.vance@revpilot.local", "close_days": 40, "tracks_next": True, "dm_known": True, "next_step_days": 8, "last_act_days": 5},
        {"deal_code": "DL-1009", "name": "Smart Factory Predictive Maintenance", "account": "OmniCorp Manufacturing", "value": 220000.0, "stage": "Negotiation", "status": "open", "owner": "jordan.taylor@revpilot.local", "close_days": 25, "tracks_next": True, "dm_known": True, "next_step_days": 4, "last_act_days": 3},
        {"deal_code": "DL-1010", "name": "Video Ingestion Platform Upgrade", "account": "Horizon Media Group", "value": 95000.0, "stage": "Discovery", "status": "open", "owner": "david.kim@revpilot.local", "close_days": 65, "tracks_next": True, "dm_known": False, "next_step_days": None, "last_act_days": 20},
        {"deal_code": "DL-1011", "name": "Edge CDN Gateway Deployment", "account": "Atlas Cloud Infrastructure", "value": 160000.0, "stage": "Proposal", "status": "open", "owner": "priya.patel@revpilot.local", "close_days": 30, "tracks_next": True, "dm_known": True, "next_step_days": 6, "last_act_days": 4},
        {"deal_code": "DL-1012", "name": "Port Logistics Telematics Engine", "account": "Beacon Freight Solutions", "value": 78000.0, "stage": "Discovery", "status": "open", "owner": "elena.rostova@revpilot.local", "close_days": 55, "tracks_next": True, "dm_known": None, "next_step_days": 10, "last_act_days": 8},
        {"deal_code": "DL-1013", "name": "Cold Chain Sensor Expansion", "account": "Northwind Logistics Demo", "value": 145000.0, "stage": "Negotiation", "status": "open", "owner": "marcus.vance@revpilot.local", "close_days": 15, "tracks_next": True, "dm_known": True, "next_step_days": None, "last_act_days": 16},
        {"deal_code": "DL-1014", "name": "Drug Discovery Pipeline Compute", "account": "Apex Global BioTech", "value": 350000.0, "stage": "Legal/Review", "status": "open", "owner": "elena.rostova@revpilot.local", "close_days": 10, "tracks_next": True, "dm_known": True, "next_step_days": 2, "last_act_days": 1},
        {"deal_code": "DL-1015", "name": "Real-time Telemetry Gateway", "account": "Acme Precision Cloud", "value": 65000.0, "stage": "Closed", "status": "won", "owner": "elena.rostova@revpilot.local", "close_days": -10, "tracks_next": True, "dm_known": True, "next_step_days": None, "last_act_days": 12},
        {"deal_code": "DL-1016", "name": "Mortgage Processing Engine", "account": "Vanguard Financial Services", "value": 180000.0, "stage": "Proposal", "status": "open", "owner": "david.kim@revpilot.local", "close_days": 40, "tracks_next": True, "dm_known": True, "next_step_days": None, "last_act_days": 22},
        {"deal_code": "DL-1017", "name": "Patient Portal Identity Verification", "account": "Starlight Health Network", "value": 90000.0, "stage": "Closed", "status": "lost", "owner": "david.kim@revpilot.local", "close_days": -5, "tracks_next": True, "dm_known": False, "next_step_days": None, "last_act_days": 30},
        {"deal_code": "DL-1018", "name": "Threat Hunting Appliance Pilot", "account": "CyberShield Defense", "value": 125000.0, "stage": "Discovery", "status": "open", "owner": "priya.patel@revpilot.local", "close_days": 45, "tracks_next": True, "dm_known": True, "next_step_days": 5, "last_act_days": 3},
        {"deal_code": "DL-1019", "name": "Point-of-Sale Integration Hub", "account": "Nexus Retail Systems", "value": 115000.0, "stage": "Proposal", "status": "open", "owner": "elena.rostova@revpilot.local", "close_days": 35, "tracks_next": True, "dm_known": True, "next_step_days": 7, "last_act_days": 5},
        {"deal_code": "DL-1020", "name": "Wind Turbine Diagnostic Feeds", "account": "Zephyr Green Energy", "value": 210000.0, "stage": "Negotiation", "status": "open", "owner": "marcus.vance@revpilot.local", "close_days": 14, "tracks_next": True, "dm_known": True, "next_step_days": None, "last_act_days": 18}
    ]

    deals = {}
    for d_data in deals_data:
        code = d_data["deal_code"]
        deal = db.query(Deal).filter(Deal.deal_code == code).first()
        if not deal:
            acc = accounts[d_data["account"]]
            u = users[d_data["owner"]]
            c_date = now + timedelta(days=d_data["close_days"])
            r_date = now + timedelta(days=d_data.get("renewal_days", d_data["close_days"])) if "renewal_days" in d_data else None
            n_step = now + timedelta(days=d_data["next_step_days"]) if d_data["next_step_days"] is not None else None
            l_act = now - timedelta(days=d_data["last_act_days"]) if d_data["last_act_days"] is not None else None

            deal = Deal(
                deal_code=code,
                external_id=code,
                account_id=acc.id,
                name=d_data["name"],
                value=d_data["value"],
                currency="USD",
                stage=d_data["stage"],
                owner_user_id=u.id,
                status=d_data["status"],
                expected_close_date=c_date,
                renewal_date=r_date,
                next_activity_at=n_step,
                last_activity_at=l_act,
                source_tracks_next_steps=d_data["tracks_next"],
                decision_maker_known=d_data["dm_known"]
            )
            db.add(deal)
            db.flush()

            # Field provenance
            for fn in ["name", "value", "stage", "status"]:
                val_str = str(getattr(deal, fn))
                is_override = False
                source_val = val_str
                last_src = "seed"
                if "manual_override" in d_data and d_data["manual_override"]["field"] == fn:
                    is_override = True
                    source_val = d_data["manual_override"]["source_val"]
                    val_str = d_data["manual_override"]["val"]
                    last_src = "manual"

                db.add(FieldProvenance(
                    entity_type="deal",
                    entity_id=deal.id,
                    field_name=fn,
                    source_value=source_val,
                    current_value=val_str,
                    previous_source_value=source_val,
                    is_overridden=is_override,
                    last_update_source=last_src
                ))

        deals[code] = deal

    db.flush()

    # 7. Activities (~80 activities with postponed meetings, replies, emails)
    # Postponements for DL-1002 (Stalled deal scenario)
    act_templates = [
        # DL-1001 (No recent response > 14 days)
        {"deal": "DL-1001", "type": "proposal_sent", "days_ago": 21, "detail": "Sent finalized enterprise proposal with multi-year tier.", "ref": "ACT-1011"},
        {"deal": "DL-1001", "type": "customer_reply", "days_ago": 21, "detail": "Customer confirmed receipt but flagged pricing concerns.", "ref": "ACT-1012"},
        # DL-1002 (Repeated postponements)
        {"deal": "DL-1002", "type": "meeting_postponed", "days_ago": 18, "detail": "VP of R&D requested reschedule due to internal budget review.", "ref": "ACT-1021"},
        {"deal": "DL-1002", "type": "meeting_postponed", "days_ago": 8, "detail": "Customer postponed technical deep dive for second consecutive time.", "ref": "ACT-1022"},
        {"deal": "DL-1002", "type": "meeting_postponed", "days_ago": 2, "detail": "Procurement team rescheduled introductory review call.", "ref": "ACT-1023"},
        # DL-1003 (Healthy deal)
        {"deal": "DL-1003", "type": "customer_reply", "days_ago": 2, "detail": "Head of Engineering replied: 'Architecture looks great, let's proceed.'", "ref": "ACT-1031"},
        {"deal": "DL-1003", "type": "meeting_scheduled", "days_ago": 1, "detail": "Security and legal alignment call confirmed for Thursday.", "ref": "ACT-1032"},
        # DL-1006 (Urgent renewal)
        {"deal": "DL-1006", "type": "email_sent", "days_ago": 15, "detail": "Sent renewal terms schedule and MSA addendum.", "ref": "ACT-1061"},
        {"deal": "DL-1006", "type": "customer_reply", "days_ago": 14, "detail": "CISO raised compliance question regarding SOC2 type II audit.", "ref": "ACT-1062"}
    ]

    # Generate additional realistic activities for all deals to reach ~80
    act_idx = 2000
    for d_code, d_obj in deals.items():
        if d_code in ["DL-1001", "DL-1002", "DL-1003", "DL-1006"]:
            continue
        act_templates.append({"deal": d_code, "type": "email_sent", "days_ago": 12, "detail": f"Follow-up email sent regarding evaluation milestone for {d_obj.name}.", "ref": f"ACT-{act_idx}"})
        act_idx += 1
        act_templates.append({"deal": d_code, "type": "customer_reply", "days_ago": 7, "detail": f"Buyer responded with stakeholder feedback on {d_obj.name}.", "ref": f"ACT-{act_idx}"})
        act_idx += 1
        act_templates.append({"deal": d_code, "type": "meeting_held", "days_ago": 4, "detail": f"Executive status review held with project champion.", "ref": f"ACT-{act_idx}"})
        act_idx += 1
        act_templates.append({"deal": d_code, "type": "meeting_scheduled", "days_ago": 1, "detail": f"Follow-up meeting scheduled on calendar for next milestone.", "ref": f"ACT-{act_idx}"})
        act_idx += 1

    for a_t in act_templates:
        existing_act = db.query(Activity).filter(Activity.source_ref == a_t["ref"]).first()
        if not existing_act:
            d = deals[a_t["deal"]]
            db.add(Activity(
                external_id=a_t["ref"],
                deal_id=d.id,
                user_id=d.owner_user_id,
                type=a_t["type"],
                occurred_at=now - timedelta(days=a_t["days_ago"]),
                detail=a_t["detail"],
                source_ref=a_t["ref"]
            ))

    db.flush()

    # 8. Conversations (~40 with realistic text, excerpts, and findings)
    conv_blueprints = [
        # CONV-1: High-value pricing objection on DL-1001
        {
            "deal": "DL-1001",
            "ref": "CALL-2043",
            "type": "call",
            "days_ago": 21,
            "urgency": "critical",
            "summary": "Commercial review call with Northwind VP of Operations.",
            "text": "Speaker 1 (Marcus Vance): Thanks for jumping on today, Tom. How are the numbers looking?\n"
                    "Speaker 2 (Tom Bradley - Buyer): Honestly, Marcus, the price is too high compared to what we budgeted.\n"
                    "Speaker 2 (Tom Bradley - Buyer): Our procurement team feels this cost is out of our range for Q4 without a heavy discount.\n"
                    "Speaker 1 (Marcus Vance): I understand Tom. We will send an updated proposal with phased billing.\n"
                    "Speaker 2 (Tom Bradley - Buyer): Okay, but until pricing is aligned, we cannot sign.",
            "topic": "pricing",
            "urgency_route": "critical"
        },
        # CONV-2: Difficult routing decision (Precedence competition)
        # Matches both 'High Urgency Pricing Escalation' (order 1) and 'Standard Pricing Review' (order 5)
        {
            "deal": "DL-1001",
            "ref": "EMAIL-2044",
            "type": "email",
            "days_ago": 19,
            "urgency": "critical",
            "summary": "Urgent pricing redline email from Northwind Finance.",
            "text": "From: tom.bradley@northwind-logistics.demo\n"
                    "To: alex.morgan@revpilot.local\n"
                    "Subject: Urgent: Commercial proposal review required\n"
                    "We need to discuss the commercial fee schedule immediately. The current pricing structure is unacceptable for our executive team.\n"
                    "Action item: schedule a follow up call with pricing leadership by tomorrow.",
            "topic": "pricing",
            "urgency_route": "critical"
        },
        # CONV-3: Ambiguous Routing Test (Triggers Unassigned Review Queue)
        {
            "deal": "DL-1005",
            "ref": "CALL-2045",
            "type": "call",
            "days_ago": 10,
            "urgency": "high",
            "summary": "Ambiguous contract terms discussion with Starlight Counsel.",
            "text": "Speaker 1 (Elena Rostova): We need clarity on clause 14.\n"
                    "Speaker 2 (Legal Counsel): This requires ambiguous contract terms review across both pricing and renewals.\n"
                    "Speaker 1: Understood, we will have team leads review the redline.",
            "topic": "ambiguous_contract",
            "urgency_route": "high"
        },
        # CONV-4: Technical concern on DL-1004
        {
            "deal": "DL-1004",
            "ref": "CALL-2046",
            "type": "call",
            "days_ago": 6,
            "urgency": "medium",
            "summary": "Architecture deep dive on Vanguard security requirements.",
            "text": "Speaker 1 (Priya Patel): Let's review the SOC2 and encryption posture.\n"
                    "Speaker 2 (Vanguard InfoSec): We have a security compliance concern with cross-region replication.\n"
                    "Speaker 1 (Priya Patel): We will provide the revised architecture whitepaper by Friday.",
            "topic": "technical",
            "urgency_route": "medium"
        },
        # CONV-5: Urgent renewal with no assigned owner (Review Queue finding)
        {
            "deal": "DL-1006",
            "ref": "CALL-2047",
            "type": "call",
            "days_ago": 8,
            "urgency": "critical",
            "summary": "Urgent customer commitment on CyberShield renewal.",
            "text": "Speaker 1: CyberShield has a critical renewal deadline approaching.\n"
                    "Speaker 2: We must have an assigned account lead confirm the terms by Wednesday.\n"
                    "Speaker 1: Flagged for unassigned review queue escalation.",
            "topic": "renewal",
            "urgency_route": "critical",
            "unassigned": True
        }
    ]

    # Add further conversations across all deals to reach ~40
    conv_count = len(conv_blueprints)
    for d_code, d_obj in list(deals.items()) * 3:
        if conv_count >= 40:
            break
        if d_code in ["DL-1001", "DL-1002"]:
            continue
        c_type = "call" if conv_count % 2 == 0 else "meeting"
        topic = "pricing" if conv_count % 3 == 0 else ("technical" if conv_count % 3 == 1 else "renewal")
        conv_blueprints.append({
            "deal": d_code,
            "ref": f"NOTE-{3000 + conv_count}",
            "type": c_type,
            "days_ago": 3 + (conv_count % 20),
            "urgency": "high" if conv_count % 5 == 0 else "medium",
            "summary": f"Alignment discussion ({c_type}) regarding {d_obj.name}.",
            "text": f"Discussion with project team for {d_obj.name}.\n"
                    f"Covered current evaluation progress, budget allocation, and operational requirements.\n"
                    f"Action item: agreed to follow up with executive sponsor next week.",
            "topic": topic,
            "urgency_route": "high" if conv_count % 5 == 0 else "medium"
        })
        conv_count += 1

    # Insert conversations and extract findings
    all_rules = db.query(RoutingRule).all()
    rules_dicts = [
        {
            "id": r.id, "name": r.name, "priority_order": r.priority_order,
            "conditions": r.conditions, "target_owner_user_id": r.target_owner_user_id,
            "target_team_id": r.target_team_id, "priority_outcome": r.priority_outcome,
            "enabled": r.enabled, "specificity": r.specificity
        }
        for r in all_rules
    ]

    for cb in conv_blueprints:
        existing_c = db.query(Conversation).filter(Conversation.source_record_ref == cb["ref"]).first()
        if not existing_c:
            d = deals[cb["deal"]]
            c_time = now - timedelta(days=cb["days_ago"])
            c_hash = hashlib.sha256(cb["text"].encode("utf-8")).hexdigest()

            # Deterministic rule extraction
            extraction = extract_evidence_and_findings(cb["text"], cb["ref"], c_time)

            assigned_id = None if cb.get("unassigned") else d.owner_user_id

            conv = Conversation(
                deal_id=d.id,
                account_id=d.account_id,
                assigned_user_id=assigned_id,
                type=cb["type"],
                occurred_at=c_time,
                summary=cb["summary"],
                customer_intent="Evaluate solution capabilities and commercial alignment",
                sentiment_label=extraction["sentiment_label"],
                sentiment_basis=extraction["sentiment_basis"],
                urgency=cb["urgency"],
                priority=cb["urgency"],
                raw_text=cb["text"],
                source_file="seed_dataset_v1.json",
                source_record_ref=cb["ref"],
                recommended_next_action="Schedule follow-up review with account team",
                routing_status="unassigned_review" if cb.get("unassigned") else "recommended",
                content_hash=c_hash
            )
            db.add(conv)
            db.flush()

            # Add evidence excerpts
            excerpt_map = {}
            for ex in extraction["excerpts"]:
                ev = EvidenceExcerpt(
                    conversation_id=conv.id,
                    source_type=ex["source_type"],
                    source_ref=ex["source_ref"],
                    excerpt_text=ex["excerpt_text"],
                    start_offset=ex["start_offset"],
                    end_offset=ex["end_offset"],
                    occurred_at=ex["occurred_at"],
                    extractor=ex["extractor"]
                )
                db.add(ev)
                db.flush()
                excerpt_map[ex["source_ref"]] = ev.id

            # Add findings linked to excerpts
            for fd in extraction["findings"]:
                ev_id = excerpt_map.get(fd["source_ref"])
                db.add(ConversationFinding(
                    conversation_id=conv.id,
                    kind=fd["kind"],
                    label=fd["label"],
                    status=fd["status"],
                    evidence_id=ev_id,
                    confidence=fd["confidence"]
                ))

            # Run routing evaluation
            route_context = {
                "topic": cb.get("topic", "pricing"),
                "urgency": cb.get("urgency_route", "medium"),
                "deal_owner_id": d.owner_user_id
            }
            route_res = evaluate_routing(route_context, rules_dicts)

            # Record routing decision
            r_dec = RoutingDecision(
                conversation_id=conv.id,
                decided_at=c_time,
                rules_evaluated=route_res["rules_evaluated"],
                matched_rule_ids=route_res["matched_rule_ids"],
                winning_rule_id=route_res["winning_rule_id"],
                recommended_owner_id=route_res["recommended_owner_id"],
                alternative_owner_id=route_res["alternative_owner_id"],
                priority=route_res["priority"],
                reason=route_res["reason"],
                status=route_res["status"],
                is_current=True
            )
            db.add(r_dec)
            conv.routing_status = route_res["status"]

    db.flush()

    # 9. Initial Risk Assessments for all Deals
    for d_code, deal in deals.items():
        convs = [c.__dict__ for c in deal.conversations]
        acts = [a.__dict__ for a in deal.activities]
        f_list = []
        for c in deal.conversations:
            for f in c.findings:
                f_dict = f.__dict__.copy()
                if f.evidence:
                    f_dict["source_ref"] = f.evidence.source_ref
                f_list.append(f_dict)

        assessment_res = assess_deal_risk(deal.__dict__, convs, f_list, acts, now=now)

        new_ass = RiskAssessment(
            deal_id=deal.id,
            assessed_at=now,
            as_of=now,
            rules_version=1,
            config_snapshot=assessment_res["config_snapshot"],
            score=assessment_res["score"],
            category=assessment_res["category"],
            data_completeness_pct=assessment_res["data_completeness_pct"],
            confidence_note=assessment_res["confidence_note"],
            trigger="scheduled",
            is_current=True
        )
        db.add(new_ass)
        db.flush()

        for s_data in assessment_res["signals"]:
            sig = RiskSignal(
                assessment_id=new_ass.id,
                signal_code=s_data["signal_code"],
                state=s_data["state"],
                severity=s_data["severity"],
                weight_applied=s_data["weight_applied"],
                score_contribution=s_data["score_contribution"],
                explanation=s_data["explanation"],
                why_it_matters=s_data["why_it_matters"],
                evidence_ids=s_data.get("evidence_ids", [])
            )
            db.add(sig)

        db.flush()

        # Create alert if High or Critical risk
        if new_ass.category in ["High", "Critical"]:
            db.add(Alert(
                deal_id=deal.id,
                assessment_id=new_ass.id,
                status="open",
                created_at=now
            ))

        # 10. Generate Follow-Up Actions
        generate_deduped_actions_for_deal(db, deal, new_ass, now)

    db.commit()

    return {
        "status": "seeded",
        "teams": db.query(Team).count(),
        "users": db.query(User).count(),
        "accounts": db.query(Account).count(),
        "deals": db.query(Deal).count(),
        "conversations": db.query(Conversation).count(),
        "activities": db.query(Activity).count(),
        "actions": db.query(FollowUpAction).count()
    }
