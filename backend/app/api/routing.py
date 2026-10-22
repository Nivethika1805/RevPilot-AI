from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.clock import get_clock
from app.models.entities import RoutingRule, RoutingDecision, Conversation, User, Team
from app.schemas.schemas import (
    RoutingRuleRead, RoutingRuleCreate, RoutingRuleUpdate,
    RoutingDecisionRead, RoutingOverrideRequest, RoutingDryRunRequest
)
from app.services.routing_engine import evaluate_routing
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/routing", tags=["Routing Engine"])

@router.get("/rules", response_model=List[RoutingRuleRead])
def list_routing_rules(db: Session = Depends(get_db)):
    rules = db.query(RoutingRule).order_by(RoutingRule.priority_order.asc(), RoutingRule.specificity.desc()).all()
    results = []
    for r in rules:
        results.append({
            "id": r.id,
            "name": r.name,
            "priority_order": r.priority_order,
            "conditions": r.conditions,
            "target_owner_user_id": r.target_owner_user_id,
            "target_owner_name": r.target_owner.name if r.target_owner else None,
            "target_team_id": r.target_team_id,
            "target_team_name": r.target_team.name if r.target_team else None,
            "priority_outcome": r.priority_outcome,
            "enabled": r.enabled,
            "version": r.version,
            "specificity": r.specificity,
            "created_at": r.created_at
        })
    return results

@router.post("/rules", response_model=RoutingRuleRead)
def create_routing_rule(req: RoutingRuleCreate, db: Session = Depends(get_db)):
    spec = len(req.conditions) if req.conditions else 1
    rule = RoutingRule(
        name=req.name,
        priority_order=req.priority_order,
        conditions=req.conditions,
        target_owner_user_id=req.target_owner_user_id,
        target_team_id=req.target_team_id,
        priority_outcome=req.priority_outcome,
        enabled=req.enabled,
        version=1,
        specificity=spec
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.put("/rules/{id}", response_model=RoutingRuleRead)
def update_routing_rule(id: int, req: RoutingRuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(RoutingRule).filter(RoutingRule.id == id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if req.name is not None:
        rule.name = req.name
    if req.priority_order is not None:
        rule.priority_order = req.priority_order
    if req.conditions is not None:
        rule.conditions = req.conditions
        rule.specificity = len(req.conditions)
    if req.target_owner_user_id is not None:
        rule.target_owner_user_id = req.target_owner_user_id
    if req.target_team_id is not None:
        rule.target_team_id = req.target_team_id
    if req.priority_outcome is not None:
        rule.priority_outcome = req.priority_outcome
    if req.enabled is not None:
        rule.enabled = req.enabled

    rule.version += 1
    db.commit()
    db.refresh(rule)
    return rule

@router.get("/review-queue")
def get_unassigned_review_queue(db: Session = Depends(get_db)):
    """
    Returns conversations that entered the unassigned review queue due to
    rule conflicts, ambiguity, or missing owners.
    """
    convs = db.query(Conversation).filter(
        Conversation.routing_status == "unassigned_review"
    ).order_by(Conversation.occurred_at.desc()).all()

    queue = []
    for c in convs:
        latest_decision = db.query(RoutingDecision).filter(
            RoutingDecision.conversation_id == c.id,
            RoutingDecision.is_current == True
        ).first()

        queue.append({
            "conversation_id": c.id,
            "source_record_ref": c.source_record_ref,
            "type": c.type,
            "summary": c.summary,
            "deal_code": c.deal.deal_code if c.deal else "N/A",
            "deal_name": c.deal.name if c.deal else "N/A",
            "urgency": c.urgency,
            "occurred_at": c.occurred_at,
            "reason": latest_decision.reason if latest_decision else "Needs manual manager assignment",
            "evaluated_rules_count": len(latest_decision.rules_evaluated) if latest_decision else 0
        })
    return queue

@router.post("/decide/{conversation_id}")
def decide_routing(conversation_id: int, db: Session = Depends(get_db)):
    c = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if a manual override is active
    latest_dec = db.query(RoutingDecision).filter(
        RoutingDecision.conversation_id == c.id,
        RoutingDecision.is_current == True
    ).first()

    if latest_dec and latest_dec.status == "overridden":
        # Overrides are preserved! Informational only
        return {
            "status": "preserved_override",
            "active_owner_id": latest_dec.override_owner_id,
            "override_reason": latest_dec.override_reason,
            "message": "Manual override preserved. Re-routing engine did not overwrite manual decision."
        }

    rules = db.query(RoutingRule).filter(RoutingRule.enabled == True).all()
    rules_dicts = [{
        "id": r.id, "name": r.name, "priority_order": r.priority_order,
        "conditions": r.conditions, "target_owner_user_id": r.target_owner_user_id,
        "target_team_id": r.target_team_id, "priority_outcome": r.priority_outcome,
        "enabled": r.enabled, "specificity": r.specificity
    } for r in rules]

    context = {
        "urgency": c.urgency,
        "type": c.type,
        "deal_owner_id": c.deal.owner_user_id if c.deal else None
    }
    # Check topics
    for f in c.findings:
        if "pricing" in f.label.lower():
            context["topic"] = "pricing"
        elif "technical" in f.label.lower():
            context["topic"] = "technical"

    decision_res = evaluate_routing(context, rules_dicts)

    # Archive previous
    db.query(RoutingDecision).filter(
        RoutingDecision.conversation_id == c.id,
        RoutingDecision.is_current == True
    ).update({"is_current": False})

    clock = get_clock()
    now = clock.now()

    new_dec = RoutingDecision(
        conversation_id=c.id,
        decided_at=now,
        rules_evaluated=decision_res["rules_evaluated"],
        matched_rule_ids=decision_res["matched_rule_ids"],
        winning_rule_id=decision_res["winning_rule_id"],
        recommended_owner_id=decision_res["recommended_owner_id"],
        alternative_owner_id=decision_res["alternative_owner_id"],
        priority=decision_res["priority"],
        reason=decision_res["reason"],
        status=decision_res["status"],
        is_current=True
    )
    db.add(new_dec)

    c.routing_status = decision_res["status"]
    if decision_res["recommended_owner_id"]:
        c.assigned_user_id = decision_res["recommended_owner_id"]

    db.commit()
    return decision_res

@router.post("/override/{conversation_id}")
def override_routing(
    conversation_id: int,
    req: RoutingOverrideRequest,
    db: Session = Depends(get_db)
):
    c = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")

    target_user = db.query(User).filter(User.id == req.target_owner_id).first()
    if not target_user:
        raise HTTPException(status_code=400, detail="Target owner user does not exist")

    clock = get_clock()
    now = clock.now()

    # Archive previous
    db.query(RoutingDecision).filter(
        RoutingDecision.conversation_id == c.id,
        RoutingDecision.is_current == True
    ).update({"is_current": False})

    override_dec = RoutingDecision(
        conversation_id=c.id,
        decided_at=now,
        rules_evaluated=[],
        matched_rule_ids=[],
        winning_rule_id=None,
        recommended_owner_id=target_user.id,
        priority="high",
        reason=f"Manual Override: {req.reason}",
        status="overridden",
        override_owner_id=target_user.id,
        override_reason=req.reason,
        is_current=True
    )
    db.add(override_dec)

    c.assigned_user_id = target_user.id
    c.routing_status = "overridden"

    log_audit_event(
        db,
        event_type="routing_override",
        entity_type="conversation",
        entity_id=c.id,
        actor_label="Manager",
        after={"assigned_user_id": target_user.id, "owner_name": target_user.name},
        reason=req.reason
    )

    db.commit()
    return {"status": "overridden", "new_owner": target_user.name, "reason": req.reason}

@router.post("/dry-run")
def dry_run_routing(req: RoutingDryRunRequest, db: Session = Depends(get_db)):
    rules = db.query(RoutingRule).filter(RoutingRule.enabled == True).all()
    rules_dicts = [{
        "id": r.id, "name": r.name, "priority_order": r.priority_order,
        "conditions": r.conditions, "target_owner_user_id": r.target_owner_user_id,
        "target_team_id": r.target_team_id, "priority_outcome": r.priority_outcome,
        "enabled": r.enabled, "specificity": r.specificity
    } for r in rules]

    return evaluate_routing(req.conditions, rules_dicts)
