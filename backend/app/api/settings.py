from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.clock import get_clock
from app.models.entities import RiskConfig, Deal, RiskAssessment, RiskSignal
from app.schemas.schemas import RiskConfigRead, RiskConfigUpdate
from app.services.risk_engine import assess_deal_risk
from app.services.action_service import generate_deduped_actions_for_deal
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("")
def get_system_settings(db: Session = Depends(get_db)):
    clock = get_clock()
    now = clock.now()
    configs = db.query(RiskConfig).all()

    return {
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "schema_version": settings.SCHEMA_VERSION,
        "as_of_date": settings.AS_OF_DATE,
        "current_time": now.isoformat(),
        "demo_mode": settings.DEMO_MODE,
        "llm_extractor_enabled": bool(settings.LLM_API_KEY),
        "extractor_in_use": "llm" if settings.LLM_API_KEY else "rules",
        "risk_signals": [{
            "id": c.id,
            "signal_code": c.signal_code,
            "weight": c.weight,
            "threshold_params": c.threshold_params,
            "enabled": c.enabled,
            "version": c.version
        } for c in configs]
    }

@router.put("/risk/{signal_code}")
def update_risk_signal_config(
    signal_code: str,
    update: RiskConfigUpdate,
    db: Session = Depends(get_db)
):
    cfg = db.query(RiskConfig).filter(RiskConfig.signal_code == signal_code).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Risk configuration for signal not found")

    before = {"weight": cfg.weight, "enabled": cfg.enabled, "threshold_params": cfg.threshold_params}

    if update.weight is not None:
        cfg.weight = update.weight
    if update.enabled is not None:
        cfg.enabled = update.enabled
    if update.threshold_params is not None:
        cfg.threshold_params = update.threshold_params

    cfg.version += 1

    log_audit_event(
        db,
        event_type="risk_config_updated",
        entity_type="risk_config",
        entity_id=cfg.id,
        actor_label="Admin",
        before=before,
        after={"weight": cfg.weight, "enabled": cfg.enabled, "threshold_params": cfg.threshold_params},
        reason=f"Updated risk configuration for {signal_code}"
    )

    db.commit()
    db.refresh(cfg)
    return {"status": "updated", "signal_code": signal_code, "version": cfg.version}

@router.post("/recompute-risk")
def recompute_all_assessments(db: Session = Depends(get_db)):
    """
    Recomputes all deal assessments using the updated active risk configurations.
    Audited.
    """
    clock = get_clock()
    now = clock.now()

    # Load active config
    cfgs = db.query(RiskConfig).all()
    active_config = {}
    for c in cfgs:
        active_config[c.signal_code] = {
            "weight": c.weight,
            "enabled": c.enabled,
            **c.threshold_params
        }

    deals = db.query(Deal).filter(Deal.status == "open").all()
    recomputed_count = 0

    for d in deals:
        convs = [c.__dict__ for c in d.conversations]
        acts = [a.__dict__ for a in d.activities]
        f_list = []
        for c in d.conversations:
            for f in c.findings:
                f_d = f.__dict__.copy()
                if f.evidence:
                    f_d["source_ref"] = f.evidence.source_ref
                f_list.append(f_d)

        res = assess_deal_risk(d.__dict__, convs, f_list, acts, config=active_config, now=now)

        # Archive old
        db.query(RiskAssessment).filter(
            RiskAssessment.deal_id == d.id,
            RiskAssessment.is_current == True
        ).update({"is_current": False})

        new_ass = RiskAssessment(
            deal_id=d.id,
            assessed_at=now,
            as_of=now,
            rules_version=2,
            config_snapshot=active_config,
            score=res["score"],
            category=res["category"],
            data_completeness_pct=res["data_completeness_pct"],
            confidence_note=res["confidence_note"],
            trigger="manual",
            is_current=True
        )
        db.add(new_ass)
        db.flush()

        for s in res["signals"]:
            db.add(RiskSignal(
                assessment_id=new_ass.id,
                signal_code=s["signal_code"],
                state=s["state"],
                severity=s["severity"],
                weight_applied=s["weight_applied"],
                score_contribution=s["score_contribution"],
                explanation=s["explanation"],
                why_it_matters=s["why_it_matters"],
                evidence_ids=s.get("evidence_ids", [])
            ))

        generate_deduped_actions_for_deal(db, d, new_ass, now)
        recomputed_count += 1

    log_audit_event(
        db,
        event_type="risk_assessments_recomputed_bulk",
        entity_type="risk_assessment",
        actor_label="Admin",
        after={"deals_recomputed": recomputed_count},
        reason="Triggered bulk recomputation from settings"
    )

    db.commit()
    return {"status": "recomputed", "deals_assessed": recomputed_count}
