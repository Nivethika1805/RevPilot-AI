from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.entities import Deal, Conversation, RiskAssessment, RiskSignal, RoutingDecision, FollowUpAction, Account

def generate_evidence_findings(db: Session, as_of: datetime) -> Dict[str, Any]:
    """
    Dynamically queries database records to generate evidence-backed revenue findings.
    """
    findings = []

    # 1. High-value deal with unresolved pricing objection AND no customer reply > 14 days
    high_val_deals = db.query(Deal).filter(
        Deal.status == "open",
        Deal.value >= 100000.0
    ).all()

    for d in high_val_deals:
        current_assessment = next((a for a in d.risk_assessments if a.is_current), None)
        if current_assessment:
            signals_map = {s.signal_code: s for s in current_assessment.signals if s.state == "detected"}
            has_pricing = "UNRESOLVED_PRICING_OBJECTION" in signals_map
            has_no_reply = "NO_RECENT_CUSTOMER_RESPONSE" in signals_map

            if has_pricing and has_no_reply:
                evidence_refs = []
                for s_code in ["UNRESOLVED_PRICING_OBJECTION", "NO_RECENT_CUSTOMER_RESPONSE"]:
                    sig = signals_map[s_code]
                    if sig.evidence_ids:
                        for ev in sig.evidence_ids:
                            evidence_refs.append(ev)

                findings.append({
                    "id": f"FINDING-HIGH-VALUE-PRICING-STALL-{d.deal_code}",
                    "title": f"High-Value Deal Stalled on Pricing Pushback ({d.deal_code})",
                    "severity": "critical",
                    "deal_id": d.id,
                    "deal_code": d.deal_code,
                    "deal_name": d.name,
                    "account_name": d.account.name if d.account else "Unknown Account",
                    "description": f"Deal '{d.name}' valued at ${d.value:,.2f} has active pricing objections without customer reply for over 14 days. Deal momentum has slipped, placing target close date at acute risk.",
                    "evidence_refs": evidence_refs,
                    "recommended_action": "Schedule an executive alignment call and prepare commercial concessions or tiered ROI breakdown."
                })
                break

    # 2. Open deals with no documented next action (where source tracks next steps)
    missing_next_deals = db.query(Deal).filter(
        Deal.status == "open",
        Deal.source_tracks_next_steps == True,
        Deal.next_activity_at == None
    ).all()

    if missing_next_deals:
        evidence_refs = []
        d_codes = []
        for d in missing_next_deals[:4]:
            d_codes.append(d.deal_code)
            evidence_refs.append({
                "source_ref": f"DEAL-{d.deal_code}",
                "occurred_at": d.updated_at.isoformat(),
                "detail": f"Deal {d.deal_code} ({d.name}) has source_tracks_next_steps=True but next_activity_at is null."
            })

        findings.append({
            "id": "FINDING-MISSING-NEXT-STEPS-CLUSTER",
            "title": f"Multiple Open Pipeline Deals Lack Documented Next Milestones ({len(missing_next_deals)} deals)",
            "severity": "high",
            "deal_id": missing_next_deals[0].id if missing_next_deals else None,
            "deal_code": ", ".join(d_codes),
            "deal_name": f"{len(missing_next_deals)} pipeline opportunities",
            "account_name": "Multiple Enterprise Accounts",
            "description": f"Audited {len(missing_next_deals)} open deals where sales tracking requires scheduled next steps, yet no forward activity or follow-up commitment is recorded in the CRM.",
            "evidence_refs": evidence_refs,
            "recommended_action": "Audit pipeline cadence in weekly 1:1s; require reps to lock in confirmed customer milestones."
        })

    # 3. Urgent renewal or commitment with no assigned owner
    urgent_unassigned_convs = db.query(Conversation).filter(
        or_(Conversation.assigned_user_id == None, Conversation.routing_status == "unassigned_review"),
        Conversation.urgency.in_(["high", "critical"])
    ).all()

    if urgent_unassigned_convs:
        c = urgent_unassigned_convs[0]
        findings.append({
            "id": f"FINDING-URGENT-UNASSIGNED-CONVERSATION-{c.source_record_ref}",
            "title": f"High-Urgency Customer Interaction In Review Queue Without Owner ({c.source_record_ref})",
            "severity": "high",
            "deal_id": c.deal_id,
            "deal_code": c.deal.deal_code if c.deal else "DL-UNASSIGNED",
            "deal_name": c.deal.name if c.deal else "Unassigned Deal",
            "account_name": c.account.name if c.account else "Unknown",
            "description": f"Customer conversation '{c.summary}' flagged with '{c.urgency}' urgency has no active owner assigned. Currently routed to Unassigned Review Queue pending manager action.",
            "evidence_refs": [{
                "source_ref": c.source_record_ref,
                "occurred_at": c.occurred_at.isoformat(),
                "detail": c.summary
            }],
            "recommended_action": "Access Unassigned Review Queue and assign dedicated account executive immediately."
        })

    # Difficult routing decision section
    competing_decision = db.query(RoutingDecision).filter(
        RoutingDecision.alternative_owner_id != None
    ).order_by(RoutingDecision.id.desc()).first()

    difficult_decision_data = None
    if competing_decision:
        c = competing_decision.conversation
        difficult_decision_data = {
            "decision_id": competing_decision.id,
            "conversation_ref": c.source_record_ref if c else "CONV-REF",
            "conversation_summary": c.summary if c else "",
            "deal_code": c.deal.deal_code if (c and c.deal) else "",
            "chosen_owner": competing_decision.recommended_owner.name if competing_decision.recommended_owner else "Assigned Owner",
            "rejected_alternative": competing_decision.alternative_owner.name if competing_decision.alternative_owner else "Alternative Candidate",
            "winning_rule": competing_decision.winning_rule.name if competing_decision.winning_rule else "Priority Rule",
            "reason": competing_decision.reason,
            "evaluated_rules_count": len(competing_decision.rules_evaluated) if competing_decision.rules_evaluated else 0
        }

    return {
        "generated_at": datetime.now(timezone.utc),
        "as_of": as_of,
        "findings": findings,
        "difficult_routing_decision": difficult_decision_data
    }

def format_findings_as_markdown(report_data: Dict[str, Any]) -> str:
    md = [
        f"# RevPilot AI — Findings & Evidence Report",
        f"**Generated:** {report_data['generated_at']} | **As Of Date:** {report_data['as_of']}",
        f"\n---\n",
        f"## Evidence-Backed Revenue Findings\n"
    ]

    for f in report_data.get("findings", []):
        md.append(f"### [{f['severity'].upper()}] {f['title']}")
        md.append(f"**Deal:** {f.get('deal_code')} — {f.get('deal_name')} ({f.get('account_name')})")
        md.append(f"**Description:** {f['description']}")
        md.append(f"**Recommended Action:** {f['recommended_action']}")
        md.append(f"\n**Source Evidence References:**")
        for ev in f.get("evidence_refs", []):
            md.append(f"- **{ev.get('source_ref')}** ({ev.get('occurred_at')}): {ev.get('detail', ev.get('label', ''))}")
        md.append(f"\n---\n")

    diff = report_data.get("difficult_routing_decision")
    if diff:
        md.append(f"## Difficult Routing Decision & Precedence Analysis")
        md.append(f"**Conversation Reference:** {diff.get('conversation_ref')}")
        md.append(f"**Summary:** {diff.get('conversation_summary')}")
        md.append(f"**Winning Assignment:** {diff.get('chosen_owner')} (via `{diff.get('winning_rule')}`)")
        md.append(f"**Rejected Candidate:** {diff.get('rejected_alternative')}")
        md.append(f"**Architectural Precedence Rationale:** {diff.get('reason')}")
        md.append(f"\n---\n")

    return "\n".join(md)
