from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.clock import get_clock
from app.models.entities import Alert, User
from app.schemas.schemas import AlertRead, AlertTransitionRequest
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/alerts", tags=["Alerts"])

VALID_TRANSITIONS = {
    "open": ["acknowledged", "in_progress", "resolved"],
    "acknowledged": ["in_progress", "resolved"],
    "in_progress": ["resolved"],
    "resolved": ["reopened"],
    "reopened": ["acknowledged", "in_progress", "resolved"]
}

@router.get("", response_model=List[AlertRead])
def list_alerts(
    db: Session = Depends(get_db),
    status: Optional[str] = None
):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    alerts = query.order_by(Alert.id.desc()).all()

    results = []
    for al in alerts:
        results.append({
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
    return results

@router.post("/{id}/transition")
def transition_alert(
    id: int,
    req: AlertTransitionRequest,
    db: Session = Depends(get_db)
):
    alert = db.query(Alert).filter(Alert.id == id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    target = req.target_status.lower()
    allowed = VALID_TRANSITIONS.get(alert.status, [])

    if target not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state transition from '{alert.status}' to '{target}'. Allowed: {allowed}"
        )

    if target in ["resolved", "reopened"] and not req.note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A explanatory note is strictly required when transitioning to '{target}'."
        )

    clock = get_clock()
    now = clock.now()
    before_status = alert.status

    alert.status = target
    alert.updated_at = now

    if target == "resolved":
        alert.resolution_note = req.note
        alert.resolved_at = now
    elif target == "reopened":
        alert.reopened_reason = req.note
        alert.resolution_note = None
        alert.resolved_at = None

    log_audit_event(
        db,
        event_type="alert_transition",
        entity_type="alert",
        entity_id=alert.id,
        actor_label="Manager",
        before={"status": before_status},
        after={"status": target, "note": req.note},
        reason=req.note
    )

    db.commit()
    db.refresh(alert)
    return {
        "status": "transitioned",
        "alert_id": alert.id,
        "new_status": alert.status,
        "note": "Alert state updated. Risk score remains unchanged (Risk != Alert != Action)."
    }
