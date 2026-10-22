from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.core.database import get_db
from app.models.entities import Conversation, Deal, Account, User, EvidenceExcerpt, ConversationFinding, RoutingDecision
from app.schemas.schemas import ConversationRead, ConversationDetail, ConversationUpdate
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=dict)
def list_conversations(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    owner_id: Optional[int] = Query(None),
    urgency: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    has_objection: Optional[bool] = Query(None),
    competitor_mentioned: Optional[bool] = Query(None),
    routing_status: Optional[str] = Query(None),
    unassigned: Optional[bool] = Query(None),
    sort_by: str = Query("occurred_at"),
    sort_order: str = Query("desc"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    query = db.query(Conversation).join(Deal).join(Account)

    if q:
        search = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Conversation.summary.ilike(search),
                Conversation.raw_text.ilike(search),
                Account.name.ilike(search),
                Deal.name.ilike(search),
                Conversation.source_record_ref.ilike(search)
            )
        )

    if type:
        query = query.filter(Conversation.type == type)
    if owner_id:
        query = query.filter(Conversation.assigned_user_id == owner_id)
    if urgency:
        query = query.filter(Conversation.urgency == urgency)
    if sentiment:
        query = query.filter(Conversation.sentiment_label == sentiment)
    if routing_status:
        query = query.filter(Conversation.routing_status == routing_status)
    if unassigned is True:
        query = query.filter(
            or_(Conversation.assigned_user_id == None, Conversation.routing_status == "unassigned_review")
        )

    if has_objection is True:
        query = query.join(ConversationFinding).filter(ConversationFinding.kind == "objection")
    elif competitor_mentioned is True:
        query = query.join(ConversationFinding).filter(ConversationFinding.kind == "competitor_mention")

    total_count = query.distinct().count()

    order_col = getattr(Conversation, sort_by, Conversation.occurred_at)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(order_col))
    else:
        query = query.order_by(desc(order_col))

    convs = query.offset(offset).limit(limit).all()

    items = []
    for c in convs:
        items.append({
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
            "deal_name": c.deal.name if c.deal else "Unknown Deal",
            "account_name": c.account.name if c.account else "Unknown Account",
            "assigned_user_name": c.assigned_user.name if c.assigned_user else "Unassigned"
        })

    return {
        "total": total_count,
        "items": items,
        "limit": limit,
        "offset": offset
    }

@router.get("/{id}", response_model=ConversationDetail)
def get_conversation_detail(id: int, db: Session = Depends(get_db)):
    c = db.query(Conversation).filter(Conversation.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")

    excerpts = []
    for ex in c.evidence_excerpts:
        excerpts.append({
            "id": ex.id,
            "conversation_id": ex.conversation_id,
            "source_type": ex.source_type,
            "source_ref": ex.source_ref,
            "excerpt_text": ex.excerpt_text,
            "start_offset": ex.start_offset,
            "end_offset": ex.end_offset,
            "occurred_at": ex.occurred_at,
            "extractor": ex.extractor,
            "created_at": ex.created_at
        })

    findings = []
    for f in c.findings:
        findings.append({
            "id": f.id,
            "conversation_id": f.conversation_id,
            "kind": f.kind,
            "label": f.label,
            "status": f.status,
            "evidence_id": f.evidence_id,
            "confidence": f.confidence,
            "created_at": f.created_at,
            "evidence": {
                "id": f.evidence.id,
                "conversation_id": f.evidence.conversation_id,
                "source_type": f.evidence.source_type,
                "source_ref": f.evidence.source_ref,
                "excerpt_text": f.evidence.excerpt_text,
                "start_offset": f.evidence.start_offset,
                "end_offset": f.evidence.end_offset,
                "occurred_at": f.evidence.occurred_at,
                "extractor": f.evidence.extractor,
                "created_at": f.evidence.created_at
            } if f.evidence else None
        })

    latest_routing = db.query(RoutingDecision).filter(
        RoutingDecision.conversation_id == c.id,
        RoutingDecision.is_current == True
    ).first()

    routing_data = None
    if latest_routing:
        routing_data = {
            "id": latest_routing.id,
            "winning_rule": latest_routing.winning_rule.name if latest_routing.winning_rule else "Unassigned",
            "recommended_owner": latest_routing.recommended_owner.name if latest_routing.recommended_owner else "Unassigned",
            "alternative_owner": latest_routing.alternative_owner.name if latest_routing.alternative_owner else None,
            "reason": latest_routing.reason,
            "status": latest_routing.status,
            "override_owner": latest_routing.override_owner.name if latest_routing.override_owner else None,
            "override_reason": latest_routing.override_reason
        }

    return {
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
        "deal_name": c.deal.name if c.deal else "Unknown Deal",
        "account_name": c.account.name if c.account else "Unknown Account",
        "assigned_user_name": c.assigned_user.name if c.assigned_user else "Unassigned",
        "raw_text": c.raw_text,
        "evidence_excerpts": excerpts,
        "findings": findings,
        "routing_decision": routing_data
    }

@router.patch("/{id}")
def update_conversation(
    id: int,
    update_data: ConversationUpdate,
    db: Session = Depends(get_db)
):
    c = db.query(Conversation).filter(Conversation.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")

    before = {"assigned_user_id": c.assigned_user_id, "priority": c.priority, "urgency": c.urgency}
    
    if update_data.assigned_user_id is not None:
        c.assigned_user_id = update_data.assigned_user_id
        if c.routing_status == "unassigned_review":
            c.routing_status = "accepted"
    if update_data.priority is not None:
        c.priority = update_data.priority
    if update_data.urgency is not None:
        c.urgency = update_data.urgency
    if update_data.recommended_next_action is not None:
        c.recommended_next_action = update_data.recommended_next_action

    log_audit_event(
        db,
        event_type="conversation_updated",
        entity_type="conversation",
        entity_id=c.id,
        actor_label="User",
        before=before,
        after={"assigned_user_id": c.assigned_user_id, "priority": c.priority, "urgency": c.urgency}
    )
    db.commit()
    db.refresh(c)
    return {"status": "updated", "id": c.id}
