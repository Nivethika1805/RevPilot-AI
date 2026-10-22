from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import FollowUpAction, Deal, Conversation, RiskAssessment, RiskSignal

PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}

def generate_deduped_actions_for_deal(
    db: Session,
    deal: Deal,
    assessment: Optional[RiskAssessment],
    now: datetime
) -> List[FollowUpAction]:
    """
    Generates recommended actions from detected risk signals and deadlines.
    Enforces dedupe_key so repeated generation never duplicates open actions.
    """
    new_actions = []
    
    if not assessment:
        return new_actions

    for signal in assessment.signals:
        if signal.state != "detected":
            continue

        dedupe_key = f"DEAL-{deal.id}:{signal.signal_code}"
        
        # Check if an action with this dedupe_key already exists in open/in_progress/snoozed status
        existing = db.query(FollowUpAction).filter(
            FollowUpAction.deal_id == deal.id,
            FollowUpAction.dedupe_key == dedupe_key,
            FollowUpAction.status.in_(["open", "in_progress", "snoozed"])
        ).first()

        if existing:
            continue

        title = ""
        reason = signal.explanation
        priority = signal.severity
        due_date = now + timedelta(days=2)
        ev_ids = signal.evidence_ids

        if signal.signal_code == "UNRESOLVED_PRICING_OBJECTION":
            title = f"Review Pricing Proposal & Commercials for {deal.name}"
            priority = "critical"
            due_date = now + timedelta(days=1)
        elif signal.signal_code == "NO_RECENT_CUSTOMER_RESPONSE":
            title = f"Schedule Customer Follow-up & Re-engagement for {deal.name}"
            priority = "high"
            due_date = now + timedelta(days=2)
        elif signal.signal_code == "MISSING_NEXT_STEP":
            title = f"Confirm Next Steps & Milestone with Buyer on {deal.name}"
            priority = "high"
            due_date = now + timedelta(days=1)
        elif signal.signal_code == "UNRESOLVED_PRODUCT_OR_IMPLEMENTATION_CONCERN":
            title = f"Arrange Technical Validation / Product Deep-Dive for {deal.name}"
            priority = "high"
            due_date = now + timedelta(days=3)
        elif signal.signal_code == "APPROACHING_DEADLINE":
            title = f"Escalate Approaching Deadline & Executive Alignment on {deal.name}"
            priority = "critical"
            due_date = now + timedelta(days=1)
        elif signal.signal_code == "REPEATED_POSTPONEMENT":
            title = f"Qualify Schedule & Re-anchor Value with Buyer on {deal.name}"
            priority = "medium"
            due_date = now + timedelta(days=3)
        elif signal.signal_code == "MISSING_DECISION_MAKER":
            title = f"Identify & Map Economic Decision Maker for {deal.name}"
            priority = "medium"
            due_date = now + timedelta(days=4)
        else:
            title = f"Review and address {signal.signal_code.replace('_', ' ').lower()}"
            priority = "medium"

        action = FollowUpAction(
            deal_id=deal.id,
            source="recommended",
            title=title,
            reason=reason,
            evidence_ids=ev_ids,
            priority=priority,
            owner_user_id=deal.owner_user_id,
            due_date=due_date,
            status="open",
            dedupe_key=dedupe_key
        )
        db.add(action)
        new_actions.append(action)

    return new_actions

def rank_actions(actions: List[FollowUpAction], deal_map: Dict[int, Deal], score_map: Dict[int, float]) -> List[FollowUpAction]:
    """
    Ranks actions deterministically:
    1. priority (critical -> high -> medium -> low)
    2. due_date (earliest first)
    3. deal_value (highest first)
    4. risk_score (highest first)
    """
    def sort_key(act: FollowUpAction):
        p_rank = PRIORITY_RANK.get(act.priority.lower(), 4)
        due = act.due_date.timestamp() if act.due_date else 9999999999
        deal = deal_map.get(act.deal_id)
        d_val = - (deal.value if deal else 0.0)
        r_score = - score_map.get(act.deal_id, 0.0)
        return (p_rank, due, d_val, r_score, act.id)

    return sorted(actions, key=sort_key)
