from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.core.database import get_db
from app.core.clock import get_clock
from app.models.entities import (
    Deal, Account, User, RiskAssessment, RiskSignal, FollowUpAction,
    Alert, Conversation, Activity, FieldProvenance, FieldConflict
)
from app.schemas.schemas import DealRead, DealDetail, DealUpdate
from app.services.audit_service import log_audit_event
from app.services.risk_engine import assess_deal_risk
from app.services.action_service import generate_deduped_actions_for_deal

router = APIRouter(prefix="/deals", tags=["Deals"])

@router.get("", response_model=dict)
def list_deals(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None),
    risk_category: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    owner_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    min_value: Optional[float] = Query(None),
    max_value: Optional[float] = Query(None),
    sort_by: str = Query("value"),
    sort_order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    query = db.query(Deal).join(Account)

    if q:
        search = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Deal.name.ilike(search),
                Deal.deal_code.ilike(search),
                Account.name.ilike(search)
            )
        )

    if stage:
        query = query.filter(Deal.stage == stage)
    if owner_id:
        query = query.filter(Deal.owner_user_id == owner_id)
    if status:
        query = query.filter(Deal.status == status)
    if min_value is not None:
        query = query.filter(Deal.value >= min_value)
    if max_value is not None:
        query = query.filter(Deal.value <= max_value)

    all_deals = query.all()

    # Join risk assessments and calculate overrides
    current_assessments = db.query(RiskAssessment).filter(RiskAssessment.is_current == True).all()
    ass_map = {a.deal_id: a for a in current_assessments}
    
    overridden_deal_ids = set(
        r[0] for r in db.query(FieldProvenance.entity_id).filter(
            FieldProvenance.entity_type == "deal",
            FieldProvenance.is_overridden == True
        ).distinct()
    )

    open_actions_counts = {}
    for r in db.query(FollowUpAction.deal_id).filter(FollowUpAction.status.in_(["open", "in_progress"])).all():
        open_actions_counts[r[0]] = open_actions_counts.get(r[0], 0) + 1

    open_alerts_counts = {}
    for r in db.query(Alert.deal_id).filter(Alert.status.in_(["open", "acknowledged"])).all():
        open_alerts_counts[r[0]] = open_alerts_counts.get(r[0], 0) + 1

    filtered_items = []
    for d in all_deals:
        ass = ass_map.get(d.id)
        if risk_category:
            rc = risk_category.lower()
            if rc in ["at_risk", "high_critical"]:
                if not ass or ass.category.lower() not in ["high", "critical"]:
                    continue
            elif not ass or ass.category.lower() != rc:
                continue


        filtered_items.append({
            "id": d.id,
            "external_id": d.external_id,
            "deal_code": d.deal_code,
            "account_id": d.account_id,
            "account_name": d.account.name if d.account else "Unknown",
            "name": d.name,
            "value": d.value,
            "currency": d.currency,
            "stage": d.stage,
            "owner_user_id": d.owner_user_id,
            "owner_name": d.owner.name if d.owner else "Unassigned",
            "status": d.status,
            "expected_close_date": d.expected_close_date,
            "renewal_date": d.renewal_date,
            "last_activity_at": d.last_activity_at,
            "next_activity_at": d.next_activity_at,
            "source_tracks_next_steps": d.source_tracks_next_steps,
            "decision_maker_known": d.decision_maker_known,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
            "current_risk_score": ass.score if ass else 0.0,
            "current_risk_category": ass.category if ass else "Low",
            "data_completeness_pct": ass.data_completeness_pct if ass else 100.0,
            "has_manual_override": d.id in overridden_deal_ids,
            "open_alerts_count": open_alerts_counts.get(d.id, 0),
            "open_actions_count": open_actions_counts.get(d.id, 0)
        })

    # In-memory sorting for dynamic fields like current_risk_score
    reverse = (sort_order.lower() == "desc")
    if sort_by in ["current_risk_score", "data_completeness_pct"]:
        filtered_items.sort(key=lambda x: x.get(sort_by, 0.0), reverse=reverse)
    elif sort_by == "value":
        filtered_items.sort(key=lambda x: x.get("value", 0.0), reverse=reverse)
    else:
        filtered_items.sort(key=lambda x: str(x.get(sort_by, "")), reverse=reverse)

    total_count = len(filtered_items)
    paged_items = filtered_items[offset: offset + limit]

    return {
        "total": total_count,
        "items": paged_items,
        "limit": limit,
        "offset": offset
    }

@router.get("/{id}", response_model=DealDetail)
def get_deal_detail(id: int, db: Session = Depends(get_db)):
    d = db.query(Deal).filter(Deal.id == id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Deal not found")

    curr_ass = db.query(RiskAssessment).filter(
        RiskAssessment.deal_id == d.id,
        RiskAssessment.is_current == True
    ).first()

    signals_read = []
    if curr_ass:
        for s in curr_ass.signals:
            signals_read.append({
                "id": s.id,
                "assessment_id": s.assessment_id,
                "signal_code": s.signal_code,
                "state": s.state,
                "severity": s.severity,
                "weight_applied": s.weight_applied,
                "score_contribution": s.score_contribution,
                "explanation": s.explanation,
                "why_it_matters": s.why_it_matters,
                "evidence_ids": s.evidence_ids
            })

    assessment_read = None
    if curr_ass:
        assessment_read = {
            "id": curr_ass.id,
            "deal_id": curr_ass.deal_id,
            "assessed_at": curr_ass.assessed_at,
            "as_of": curr_ass.as_of,
            "rules_version": curr_ass.rules_version,
            "config_snapshot": curr_ass.config_snapshot,
            "score": curr_ass.score,
            "category": curr_ass.category,
            "data_completeness_pct": curr_ass.data_completeness_pct,
            "confidence_note": curr_ass.confidence_note,
            "trigger": curr_ass.trigger,
            "previous_assessment_id": curr_ass.previous_assessment_id,
            "is_current": curr_ass.is_current,
            "signals": signals_read
        }

    # Conversations
    recent_convs = []
    for c in d.conversations:
        recent_convs.append({
            "id": c.id,
            "external_id": c.external_id,
            "deal_id": c.deal_id,
            "account_id": c.account_id,
            "assigned_user_id": c.assigned_user_id,
            "type": c.type,
            "occurred_at": c.occurred_at,
            "summary": c.summary,
            "customer_intent": c.customer_intent,
            "sentiment_label": c.sentiment_label,
            "sentiment_basis": c.sentiment_basis,
            "urgency": c.urgency,
            "priority": c.priority,
            "source_file": c.source_file,
            "source_record_ref": c.source_record_ref,
            "recommended_next_action": c.recommended_next_action,
            "routing_status": c.routing_status,
            "created_at": c.created_at,
            "deal_name": d.name,
            "account_name": d.account.name if d.account else "",
            "assigned_user_name": c.assigned_user.name if c.assigned_user else "Unassigned"
        })

    # Activities
    recent_acts = []
    for a in d.activities:
        recent_acts.append({
            "id": a.id,
            "external_id": a.external_id,
            "deal_id": a.deal_id,
            "user_id": a.user_id,
            "type": a.type,
            "occurred_at": a.occurred_at,
            "detail": a.detail,
            "source_ref": a.source_ref,
            "created_at": a.created_at,
            "user_name": a.user.name if a.user else "System"
        })

    # Provenance
    provs = db.query(FieldProvenance).filter(
        FieldProvenance.entity_type == "deal",
        FieldProvenance.entity_id == d.id
    ).all()
    prov_dicts = []
    has_manual_override = False
    for p in provs:
        if p.is_overridden:
            has_manual_override = True
        prov_dicts.append({
            "field_name": p.field_name,
            "source_value": p.source_value,
            "current_value": p.current_value,
            "previous_source_value": p.previous_source_value,
            "is_overridden": p.is_overridden,
            "last_update_source": p.last_update_source,
            "updated_at": p.updated_at
        })

    # Alerts
    alerts_read = []
    for al in d.alerts:
        alerts_read.append({
            "id": al.id,
            "deal_id": al.deal_id,
            "assessment_id": al.assessment_id,
            "status": al.status,
            "resolution_note": al.resolution_note,
            "resolved_by": al.resolved_by,
            "resolved_by_name": al.resolver.name if al.resolver else None,
            "resolved_at": al.resolved_at,
            "reopened_reason": al.reopened_reason,
            "created_at": al.created_at
        })

    # Actions
    actions_read = []
    for act in d.actions:
        actions_read.append({
            "id": act.id,
            "deal_id": act.deal_id,
            "deal_name": d.name,
            "deal_code": d.deal_code,
            "account_name": d.account.name if d.account else "",
            "conversation_id": act.conversation_id,
            "source": act.source,
            "title": act.title,
            "reason": act.reason,
            "evidence_ids": act.evidence_ids,
            "priority": act.priority,
            "owner_user_id": act.owner_user_id,
            "owner_name": act.owner.name if act.owner else "Unassigned",
            "due_date": act.due_date,
            "status": act.status,
            "snoozed_until": act.snoozed_until,
            "dismissed_reason": act.dismissed_reason,
            "notes": act.notes,
            "dedupe_key": act.dedupe_key,
            "created_at": act.created_at,
            "completed_at": act.completed_at,
            "notes_list": []
        })

    return {
        "id": d.id,
        "external_id": d.external_id,
        "deal_code": d.deal_code,
        "account_id": d.account_id,
        "account_name": d.account.name if d.account else "Unknown",
        "name": d.name,
        "value": d.value,
        "currency": d.currency,
        "stage": d.stage,
        "owner_user_id": d.owner_user_id,
        "owner_name": d.owner.name if d.owner else "Unassigned",
        "status": d.status,
        "expected_close_date": d.expected_close_date,
        "renewal_date": d.renewal_date,
        "last_activity_at": d.last_activity_at,
        "next_activity_at": d.next_activity_at,
        "source_tracks_next_steps": d.source_tracks_next_steps,
        "decision_maker_known": d.decision_maker_known,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
        "current_risk_score": curr_ass.score if curr_ass else 0.0,
        "current_risk_category": curr_ass.category if curr_ass else "Low",
        "data_completeness_pct": curr_ass.data_completeness_pct if curr_ass else 100.0,
        "has_manual_override": has_manual_override,
        "open_alerts_count": len([a for a in d.alerts if a.status in ["open", "acknowledged"]]),
        "open_actions_count": len([a for a in d.actions if a.status in ["open", "in_progress"]]),
        "current_assessment": assessment_read,
        "recent_conversations": recent_convs,
        "recent_activities": recent_acts,
        "actions": actions_read,
        "alerts": alerts_read,
        "field_provenances": prov_dicts
    }

@router.patch("/{id}")
def update_deal_manual(
    id: int,
    patch_data: DealUpdate,
    db: Session = Depends(get_db)
):
    """
    Provenance-tracked manual field edit.
    Enforces manual correction policy: current_value = manual_val, is_overridden = True, last_update_source = 'manual'.
    """
    d = db.query(Deal).filter(Deal.id == id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Deal not found")

    clock = get_clock()
    now = clock.now()

    before_state = {"name": d.name, "value": d.value, "stage": d.stage}

    # Track fields
    field_updates = patch_data.model_dump(exclude_unset=True)
    for f_name, new_val in field_updates.items():
        curr_val = getattr(d, f_name)
        if new_val != curr_val:
            setattr(d, f_name, new_val)
            
            # Update FieldProvenance
            prov = db.query(FieldProvenance).filter(
                FieldProvenance.entity_type == "deal",
                FieldProvenance.entity_id == d.id,
                FieldProvenance.field_name == f_name
            ).first()

            if not prov:
                prov = FieldProvenance(
                    entity_type="deal",
                    entity_id=d.id,
                    field_name=f_name,
                    source_value=str(curr_val),
                    current_value=str(new_val),
                    previous_source_value=str(curr_val),
                    is_overridden=True,
                    last_update_source="manual",
                    updated_at=now
                )
                db.add(prov)
            else:
                prov.current_value = str(new_val)
                prov.is_overridden = True
                prov.last_update_source = "manual"
                prov.updated_at = now

    d.updated_at = now

    log_audit_event(
        db,
        event_type="deal_manual_correction",
        entity_type="deal",
        entity_id=d.id,
        actor_label="User",
        before=before_state,
        after={k: getattr(d, k) for k in field_updates.keys()},
        reason="Manual correction entered via deal cockpit"
    )

    db.commit()
    db.refresh(d)
    return {"status": "updated", "id": d.id}
