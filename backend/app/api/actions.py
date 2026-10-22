from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.clock import get_clock
from app.models.entities import FollowUpAction, ActionNote, Deal, User, RiskAssessment
from app.schemas.schemas import (
    FollowUpActionRead, FollowUpActionCreate, FollowUpActionUpdate,
    ActionNoteRead, ActionNoteCreate
)
from app.services.action_service import rank_actions, generate_deduped_actions_for_deal
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/actions", tags=["Action Queue"])

@router.get("", response_model=List[FollowUpActionRead])
def list_actions(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    owner_id: Optional[int] = Query(None),
    deal_id: Optional[int] = Query(None)
):
    query = db.query(FollowUpAction)

    if status:
        query = query.filter(FollowUpAction.status == status)
    else:
        # Default show active (open, in_progress, snoozed)
        query = query.filter(FollowUpAction.status.in_(["open", "in_progress", "snoozed"]))

    if priority:
        query = query.filter(FollowUpAction.priority == priority)
    if owner_id:
        query = query.filter(FollowUpAction.owner_user_id == owner_id)
    if deal_id:
        query = query.filter(FollowUpAction.deal_id == deal_id)

    raw_actions = query.all()

    deals = {d.id: d for d in db.query(Deal).all()}
    assessments = db.query(RiskAssessment).filter(RiskAssessment.is_current == True).all()
    score_map = {a.deal_id: a.score for a in assessments}

    ranked = rank_actions(raw_actions, deals, score_map)

    results = []
    for act in ranked:
        d = deals.get(act.deal_id)
        notes_read = []
        for n in act.action_notes:
            notes_read.append({
                "id": n.id,
                "action_id": n.action_id,
                "author_id": n.author_id,
                "author_name": n.author.name if n.author else "System",
                "body": n.body,
                "created_at": n.created_at
            })

        results.append({
            "id": act.id,
            "deal_id": act.deal_id,
            "deal_name": d.name if d else "Unknown Deal",
            "deal_code": d.deal_code if d else "DL-NA",
            "account_name": d.account.name if (d and d.account) else "Unknown",
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
            "notes_list": notes_read
        })
    return results

@router.post("", response_model=FollowUpActionRead)
def create_action(req: FollowUpActionCreate, db: Session = Depends(get_db)):
    clock = get_clock()
    now = clock.now()

    deal = db.query(Deal).filter(Deal.id == req.deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    action = FollowUpAction(
        deal_id=deal.id,
        conversation_id=req.conversation_id,
        source="manual",
        title=req.title,
        reason=req.reason,
        priority=req.priority,
        owner_user_id=req.owner_user_id or deal.owner_user_id,
        due_date=req.due_date or (now + timedelta(days=2)),
        status="open",
        notes=req.notes
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    log_audit_event(
        db,
        event_type="action_created_manual",
        entity_type="action",
        entity_id=action.id,
        actor_label="User",
        after={"title": action.title, "priority": action.priority}
    )
    db.commit()

    return {
        "id": action.id,
        "deal_id": deal.id,
        "deal_name": deal.name,
        "deal_code": deal.deal_code,
        "account_name": deal.account.name if deal.account else "",
        "conversation_id": action.conversation_id,
        "source": action.source,
        "title": action.title,
        "reason": action.reason,
        "evidence_ids": action.evidence_ids,
        "priority": action.priority,
        "owner_user_id": action.owner_user_id,
        "owner_name": action.owner.name if action.owner else "Unassigned",
        "due_date": action.due_date,
        "status": action.status,
        "snoozed_until": action.snoozed_until,
        "dismissed_reason": action.dismissed_reason,
        "notes": action.notes,
        "dedupe_key": action.dedupe_key,
        "created_at": action.created_at,
        "completed_at": action.completed_at,
        "notes_list": []
    }

@router.patch("/{id}")
def update_action(
    id: int,
    req: FollowUpActionUpdate,
    db: Session = Depends(get_db)
):
    action = db.query(FollowUpAction).filter(FollowUpAction.id == id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    clock = get_clock()
    now = clock.now()
    before_state = {"status": action.status, "priority": action.priority, "owner": action.owner_user_id}

    if req.status == "dismissed" and not req.dismissed_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A dismissal reason is strictly required when dismissing an action."
        )

    if req.status is not None:
        action.status = req.status
        if req.status == "completed":
            action.completed_at = now
    if req.priority is not None:
        action.priority = req.priority
    if req.owner_user_id is not None:
        action.owner_user_id = req.owner_user_id
    if req.due_date is not None:
        action.due_date = req.due_date
    if req.snoozed_until is not None:
        action.snoozed_until = req.snoozed_until
        action.status = "snoozed"
    if req.dismissed_reason is not None:
        action.dismissed_reason = req.dismissed_reason
    if req.notes is not None:
        action.notes = req.notes

    action.updated_at = now

    log_audit_event(
        db,
        event_type="action_status_change",
        entity_type="action",
        entity_id=action.id,
        actor_label="User",
        before=before_state,
        after={"status": action.status, "priority": action.priority, "reason": req.dismissed_reason},
        reason=req.dismissed_reason or "Action updated"
    )

    db.commit()
    db.refresh(action)
    return {"status": "updated", "action_id": action.id, "new_status": action.status}

@router.post("/{id}/notes", response_model=ActionNoteRead)
def add_action_note(
    id: int,
    req: ActionNoteCreate,
    db: Session = Depends(get_db)
):
    action = db.query(FollowUpAction).filter(FollowUpAction.id == id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    note = ActionNote(
        action_id=action.id,
        body=req.body
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {
        "id": note.id,
        "action_id": note.action_id,
        "author_id": None,
        "author_name": "User",
        "body": note.body,
        "created_at": note.created_at
    }

@router.post("/regenerate")
def regenerate_all_actions(db: Session = Depends(get_db)):
    """
    Re-runs deduplicated action generation across all active deals and assessments.
    """
    clock = get_clock()
    now = clock.now()
    deals = db.query(Deal).filter(Deal.status == "open").all()
    created_count = 0

    for d in deals:
        curr_ass = db.query(RiskAssessment).filter(
            RiskAssessment.deal_id == d.id,
            RiskAssessment.is_current == True
        ).first()
        new_acts = generate_deduped_actions_for_deal(db, d, curr_ass, now)
        created_count += len(new_acts)

    db.commit()
    return {"status": "regenerated", "new_actions_created": created_count}
