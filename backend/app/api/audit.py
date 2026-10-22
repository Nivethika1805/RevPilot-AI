from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.entities import AuditEvent
from app.schemas.schemas import AuditEventRead

router = APIRouter(prefix="/audit", tags=["Audit Trail"])

@router.get("", response_model=List[AuditEventRead])
def list_audit_events(
    db: Session = Depends(get_db),
    event_type: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    actor_label: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    query = db.query(AuditEvent)

    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditEvent.entity_id == entity_id)
    if actor_label:
        query = query.filter(AuditEvent.actor_label.ilike(f"%{actor_label}%"))

    events = query.order_by(desc(AuditEvent.occurred_at), desc(AuditEvent.id)).offset(offset).limit(limit).all()
    return events
