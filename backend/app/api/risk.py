from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.clock import get_clock
from app.models.entities import (
    Deal, RiskAssessment, RiskSignal, Activity, Conversation,
    EvidenceExcerpt, ConversationFinding, Alert, FollowUpAction
)
from app.schemas.schemas import (
    ReplayResponse, SimulationRequest, SimulationResponse, CommitSimulationRequest
)
from app.services.risk_engine import assess_deal_risk
from app.services.action_service import generate_deduped_actions_for_deal
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/risk", tags=["Risk Engine"])

@router.get("/deal/{deal_id}/history")
def get_deal_risk_history(deal_id: int, db: Session = Depends(get_db)):
    assessments = db.query(RiskAssessment).filter(
        RiskAssessment.deal_id == deal_id
    ).order_by(RiskAssessment.id.desc()).all()

    history = []
    for idx, a in enumerate(assessments):
        prev = assessments[idx + 1] if idx + 1 < len(assessments) else None
        delta = round(a.score - prev.score, 1) if prev else 0.0

        history.append({
            "id": a.id,
            "assessed_at": a.assessed_at,
            "score": a.score,
            "category": a.category,
            "trigger": a.trigger,
            "score_delta": delta,
            "is_current": a.is_current,
            "signals": [{
                "code": s.signal_code,
                "state": s.state,
                "score_contribution": s.score_contribution
            } for s in a.signals]
        })
    return history

@router.get("/replay/{assessment_id}", response_model=ReplayResponse)
def replay_assessment(assessment_id: int, db: Session = Depends(get_db)):
    ass = db.query(RiskAssessment).filter(RiskAssessment.id == assessment_id).first()
    if not ass:
        raise HTTPException(status_code=404, detail="Risk assessment not found")

    deal = ass.deal
    if not deal:
        raise HTTPException(status_code=404, detail="Deal for assessment not found")

    # Inputs considered at time of assessment
    convs = [c.__dict__ for c in deal.conversations if c.occurred_at <= ass.assessed_at]
    acts = [a.__dict__ for a in deal.activities if a.occurred_at <= ass.assessed_at]
    f_list = []
    for c in deal.conversations:
        if c.occurred_at <= ass.assessed_at:
            for f in c.findings:
                f_dict = f.__dict__.copy()
                if f.evidence:
                    f_dict["source_ref"] = f.evidence.source_ref
                f_list.append(f_dict)

    # Re-compute strictly from stored config snapshot and inputs
    recomputed = assess_deal_risk(
        deal_dict=deal.__dict__,
        conversations=convs,
        findings=f_list,
        activities=acts,
        config=ass.config_snapshot,
        now=ass.as_of
    )

    matches_stored = (abs(recomputed["score"] - ass.score) < 0.01)

    # Calculate delta vs previous
    prev_ass = db.query(RiskAssessment).filter(RiskAssessment.id == ass.previous_assessment_id).first() if ass.previous_assessment_id else None
    score_delta = round(ass.score - prev_ass.score, 1) if prev_ass else 0.0

    curr_signals = set(s["signal_code"] for s in recomputed["signals"] if s["state"] == "detected")
    prev_signals = set(s.signal_code for s in prev_ass.signals if s.state == "detected") if prev_ass else set()

    signals_added = list(curr_signals - prev_signals)
    signals_removed = list(prev_signals - curr_signals)

    return {
        "assessment_id": ass.id,
        "stored_score": ass.score,
        "recomputed_score": recomputed["score"],
        "matches_stored": matches_stored,
        "replay_matches_stored_result": matches_stored,
        "stored_rules_version": ass.rules_version,
        "stored_category": ass.category,
        "recomputed_category": recomputed["category"],
        "score_delta_vs_previous": score_delta,
        "signals_added": signals_added,
        "signals_removed": signals_removed,
        "input_records": {
            "deal_code": deal.deal_code,
            "conversations_considered": len(convs),
            "activities_considered": len(acts),
            "findings_considered": len(f_list)
        },
        "signals": recomputed["signals"]
    }

@router.post("/simulate", response_model=SimulationResponse)
def simulate_risk_change(req: SimulationRequest, db: Session = Depends(get_db)):
    """
    Pure in-memory what-if simulator.
    MUST NOT write to database, mutate rows, or create audit events!
    """
    deal = db.query(Deal).filter(Deal.id == req.deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    clock = get_clock()
    now = clock.now()

    curr_ass = db.query(RiskAssessment).filter(
        RiskAssessment.deal_id == deal.id,
        RiskAssessment.is_current == True
    ).first()

    baseline_score = curr_ass.score if curr_ass else 0.0
    baseline_cat = curr_ass.category if curr_ass else "Low"

    # Make in-memory copies of deal, activities, conversations, findings
    sim_deal = deal.__dict__.copy()
    sim_acts = [a.__dict__.copy() for a in deal.activities]
    sim_convs = [c.__dict__.copy() for c in deal.conversations]
    sim_findings = []
    for c in deal.conversations:
        for f in c.findings:
            f_d = f.__dict__.copy()
            if f.evidence:
                f_d["source_ref"] = f.evidence.source_ref
            sim_findings.append(f_d)

    # Apply hypothetical changes
    hypo = req.hypothetical_changes
    if hypo.get("add_customer_reply"):
        sim_acts.append({
            "type": "customer_reply",
            "occurred_at": now,
            "detail": "Hypothetical customer confirmation response received today.",
            "source_ref": "SIM-ACT-REPLY"
        })
        sim_deal["last_activity_at"] = now

    if hypo.get("resolve_pricing_objection"):
        sim_findings = [f for f in sim_findings if "pricing" not in f.get("label", "").lower()]

    if hypo.get("resolve_technical_objection"):
        sim_findings = [f for f in sim_findings if not any(k in f.get("label", "").lower() for k in ["technical", "implementation", "product"])]

    if hypo.get("schedule_next_step"):
        sim_deal["next_activity_at"] = now + timedelta(days=5)

    if hypo.get("confirm_decision_maker"):
        sim_deal["decision_maker_known"] = True

    # Recompute risk on in-memory structures
    recomputed = assess_deal_risk(
        deal_dict=sim_deal,
        conversations=sim_convs,
        findings=sim_findings,
        activities=sim_acts,
        now=now
    )

    sim_score = recomputed["score"]
    sim_cat = recomputed["category"]
    delta = round(sim_score - baseline_score, 1)

    baseline_detected = set(s.signal_code for s in curr_ass.signals if s.state == "detected") if curr_ass else set()
    sim_detected = set(s["signal_code"] for s in recomputed["signals"] if s["state"] == "detected")

    resolved_signals = list(baseline_detected - sim_detected)
    remaining_signals = list(sim_detected)
    new_detected = list(sim_detected - baseline_detected)

    rec_actions = []
    for s in recomputed["signals"]:
        if s["state"] == "detected":
            rec_actions.append(f"Action needed for: {s['signal_code']}")

    return {
        "deal_id": deal.id,
        "deal_code": deal.deal_code,
        "deal_name": deal.name,
        "as_of": now,
        "baseline_score": baseline_score,
        "baseline_category": baseline_cat,
        "simulated_score": sim_score,
        "simulated_category": sim_cat,
        "score_delta": delta,
        "signals_resolved": resolved_signals,
        "signals_remaining": remaining_signals,
        "new_signals_detected": new_detected,
        "recommended_actions": rec_actions,
        "disclaimer": "SIMULATION — not saved. A lower risk index does not mean the deal will close."
    }

@router.post("/simulate/commit")
def commit_simulated_change(req: CommitSimulationRequest, db: Session = Depends(get_db)):
    """
    Explicitly commits the hypothetical changes into real database records:
    Adds real activity/resolution, assesses deal risk, generates actions, logs audit.
    """
    deal = db.query(Deal).filter(Deal.id == req.deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    clock = get_clock()
    now = clock.now()

    hypo = req.hypothetical_changes
    applied_changes = []

    if hypo.get("add_customer_reply"):
        act = Activity(
            deal_id=deal.id,
            user_id=deal.owner_user_id,
            type="customer_reply",
            occurred_at=now,
            detail=f"Customer response recorded via simulation commit: {req.note}",
            source_ref=f"ACT-COMMIT-{int(now.timestamp())}"
        )
        db.add(act)
        deal.last_activity_at = now
        applied_changes.append("Recorded customer reply activity")

    if hypo.get("resolve_pricing_objection"):
        for c in deal.conversations:
            for f in c.findings:
                if "pricing" in f.label.lower():
                    f.status = "resolved"
        applied_changes.append("Marked pricing objections as resolved")

    if hypo.get("schedule_next_step"):
        deal.next_activity_at = now + timedelta(days=5)
        applied_changes.append("Scheduled confirmed next step in 5 days")

    if hypo.get("confirm_decision_maker"):
        deal.decision_maker_known = True
        applied_changes.append("Confirmed executive decision maker status")

    deal.updated_at = now

    # Re-assess
    convs = [c.__dict__ for c in deal.conversations]
    acts = [a.__dict__ for a in deal.activities]
    f_list = []
    for c in deal.conversations:
        for f in c.findings:
            f_d = f.__dict__.copy()
            if f.evidence:
                f_d["source_ref"] = f.evidence.source_ref
            f_list.append(f_d)

    new_assessment_res = assess_deal_risk(deal.__dict__, convs, f_list, acts, now=now)

    # Archive previous
    db.query(RiskAssessment).filter(
        RiskAssessment.deal_id == deal.id,
        RiskAssessment.is_current == True
    ).update({"is_current": False})

    new_ass = RiskAssessment(
        deal_id=deal.id,
        assessed_at=now,
        as_of=now,
        rules_version=1,
        config_snapshot=new_assessment_res["config_snapshot"],
        score=new_assessment_res["score"],
        category=new_assessment_res["category"],
        data_completeness_pct=new_assessment_res["data_completeness_pct"],
        confidence_note=new_assessment_res["confidence_note"],
        trigger="simulation_commit",
        is_current=True
    )
    db.add(new_ass)
    db.flush()

    for s_data in new_assessment_res["signals"]:
        db.add(RiskSignal(
            assessment_id=new_ass.id,
            signal_code=s_data["signal_code"],
            state=s_data["state"],
            severity=s_data["severity"],
            weight_applied=s_data["weight_applied"],
            score_contribution=s_data["score_contribution"],
            explanation=s_data["explanation"],
            why_it_matters=s_data["why_it_matters"],
            evidence_ids=s_data.get("evidence_ids", [])
        ))

    # Deduped actions
    generate_deduped_actions_for_deal(db, deal, new_ass, now)

    log_audit_event(
        db,
        event_type="simulation_committed",
        entity_type="deal",
        entity_id=deal.id,
        actor_label="Manager",
        after={"applied_changes": applied_changes, "new_score": new_ass.score},
        reason=req.note
    )

    db.commit()
    return {
        "status": "committed",
        "deal_id": deal.id,
        "new_score": new_ass.score,
        "new_category": new_ass.category,
        "applied_changes": applied_changes
    }
