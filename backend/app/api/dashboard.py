from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.clock import get_clock
from app.core.database import get_db
from app.models.entities import (
    Deal, Conversation, Activity, RiskAssessment, FollowUpAction, Alert, User
)
from app.schemas.schemas import DashboardMetricsResponse
from app.services.action_service import rank_actions

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/metrics", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    owner_id: int | None = Query(None),
    stage: str | None = Query(None)
):
    clock = get_clock()
    now = clock.now()

    # Query open deals
    deal_query = db.query(Deal).filter(Deal.status == "open")
    if owner_id:
        deal_query = deal_query.filter(Deal.owner_user_id == owner_id)
    if stage:
        deal_query = deal_query.filter(Deal.stage == stage)

    open_deals = deal_query.all()
    total_open_deals = len(open_deals)
    total_open_pipeline_value = sum(d.value for d in open_deals)

    # Risk distribution & at risk count
    current_assessments = db.query(RiskAssessment).filter(RiskAssessment.is_current == True).all()
    ass_map = {a.deal_id: a for a in current_assessments}
    
    risk_distribution = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    at_risk_count = 0
    deal_score_map = {}

    for d in open_deals:
        ass = ass_map.get(d.id)
        if ass:
            risk_distribution[ass.category] = risk_distribution.get(ass.category, 0) + 1
            deal_score_map[d.id] = ass.score
            if ass.category in ["High", "Critical"]:
                at_risk_count += 1
        else:
            risk_distribution["Low"] += 1
            deal_score_map[d.id] = 0.0

    # High priority conversations
    high_priority_convs = db.query(Conversation).filter(
        Conversation.urgency.in_(["high", "critical"])
    ).count()

    # Overdue follow ups
    overdue_actions_count = db.query(FollowUpAction).filter(
        FollowUpAction.status.in_(["open", "in_progress"]),
        FollowUpAction.due_date != None,
        FollowUpAction.due_date < now
    ).count()

    # Stage distribution
    stage_dist: Dict[str, Dict[str, Any]] = {}
    for d in open_deals:
        if d.stage not in stage_dist:
            stage_dist[d.stage] = {"count": 0, "value": 0.0}
        stage_dist[d.stage]["count"] += 1
        stage_dist[d.stage]["value"] += d.value

    # Recent activities
    recent_acts = db.query(Activity).order_by(Activity.occurred_at.desc()).limit(8).all()
    recent_acts_read = []
    for a in recent_acts:
        a_dict = {
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
        }
        recent_acts_read.append(a_dict)

    # Team performance indicators
    reps = db.query(User).filter(User.role.in_(["rep", "manager"])).all()
    team_perf = []
    for r in reps:
        rep_open_deals = [d for d in open_deals if d.owner_user_id == r.id]
        rep_overdue = db.query(FollowUpAction).filter(
            FollowUpAction.owner_user_id == r.id,
            FollowUpAction.status.in_(["open", "in_progress"]),
            FollowUpAction.due_date != None,
            FollowUpAction.due_date < now
        ).count()
        rep_completed = db.query(FollowUpAction).filter(
            FollowUpAction.owner_user_id == r.id,
            FollowUpAction.status == "completed"
        ).count()
        team_perf.append({
            "rep_name": r.name,
            "open_deals": len(rep_open_deals),
            "pipeline_value": sum(d.value for d in rep_open_deals),
            "overdue_actions": rep_overdue,
            "completed_actions": rep_completed
        })

    # Recent alerts
    recent_alerts = db.query(Alert).filter(Alert.status.in_(["open", "acknowledged"])).order_by(Alert.id.desc()).limit(5).all()

    # Prioritized "What Should I Do Today?" queue preview
    open_actions = db.query(FollowUpAction).filter(FollowUpAction.status.in_(["open", "in_progress"])).all()
    deal_map = {d.id: d for d in db.query(Deal).all()}
    ranked = rank_actions(open_actions, deal_map, deal_score_map)[:7]

    ranked_actions_read = []
    for act in ranked:
        d = deal_map.get(act.deal_id)
        ranked_actions_read.append({
            "id": act.id,
            "deal_id": act.deal_id,
            "deal_name": d.name if d else "Unknown Deal",
            "deal_code": d.deal_code if d else "DL-NA",
            "account_name": d.account.name if (d and d.account) else "Unknown Account",
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
        "as_of": now,
        "total_open_pipeline_value": total_open_pipeline_value,
        "total_open_deals": total_open_deals,
        "at_risk_deals_count": at_risk_count,
        "high_priority_conversations_count": high_priority_convs,
        "overdue_follow_ups_count": overdue_actions_count,
        "risk_distribution": risk_distribution,
        "stage_distribution": stage_dist,
        "recent_activities": recent_acts_read,
        "team_performance": team_perf,
        "recent_alerts": recent_alerts,
        "what_should_i_do_today": ranked_actions_read
    }
