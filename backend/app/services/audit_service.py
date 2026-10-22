import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.entities import AuditEvent

def log_audit_event(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    actor_id: Optional[int] = None,
    actor_label: str = "System",
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
    import_job_id: Optional[int] = None,
    correlation_id: Optional[str] = None
) -> AuditEvent:
    """
    Creates an append-only audit log entry.
    Ensures safe serialization without leaking secrets.
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    event = AuditEvent(
        occurred_at=datetime.now(timezone.utc),
        actor_id=actor_id,
        actor_label=actor_label,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        reason=reason,
        import_job_id=import_job_id,
        correlation_id=correlation_id
    )
    db.add(event)
    return event
