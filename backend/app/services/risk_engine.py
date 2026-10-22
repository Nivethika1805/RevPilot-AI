from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

DEFAULT_RISK_CONFIG = {
    "NO_RECENT_CUSTOMER_RESPONSE": {"weight": 20.0, "threshold_days": 14, "enabled": True},
    "UNRESOLVED_PRICING_OBJECTION": {"weight": 25.0, "enabled": True},
    "REPEATED_POSTPONEMENT": {"weight": 15.0, "threshold_postpones": 2, "lookback_days": 45, "enabled": True},
    "MISSING_NEXT_STEP": {"weight": 15.0, "enabled": True},
    "UNRESOLVED_PRODUCT_OR_IMPLEMENTATION_CONCERN": {"weight": 15.0, "enabled": True},
    "APPROACHING_DEADLINE": {"weight": 15.0, "threshold_days": 30, "enabled": True},
    "REPEATED_CUSTOMER_CONCERN": {"weight": 10.0, "min_conversations": 2, "enabled": True},
    "MISSING_DECISION_MAKER": {"weight": 10.0, "enabled": True},
}

def determine_risk_category(score: float) -> str:
    if score >= 75.0:
        return "Critical"
    elif score >= 50.0:
        return "High"
    elif score >= 25.0:
        return "Medium"
    return "Low"

def assess_deal_risk(
    deal_dict: Dict[str, Any],
    conversations: List[Dict[str, Any]],
    findings: List[Dict[str, Any]],
    activities: List[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Pure deterministic risk assessment function.
    Evaluates risk signals as: 'detected', 'not_detected', or 'unknown'.
    Only 'detected' contributes to the score.
    'unknown' contributes 0 and lowers Data Completeness %.
    """
    if config is None:
        config = DEFAULT_RISK_CONFIG
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    signals = []
    total_signals_evaluated = len(config)
    known_signals_count = 0

    # 1. NO_RECENT_CUSTOMER_RESPONSE
    cfg_reply = config.get("NO_RECENT_CUSTOMER_RESPONSE", DEFAULT_RISK_CONFIG["NO_RECENT_CUSTOMER_RESPONSE"])
    if cfg_reply.get("enabled", True):
        threshold_days = cfg_reply.get("threshold_days", 14)
        customer_activities = [
            a for a in activities 
            if a.get("type") in ["customer_reply", "meeting_held"]
        ]
        if not customer_activities and not conversations:
            # Missing customer activity data completely -> Unknown!
            signals.append({
                "signal_code": "NO_RECENT_CUSTOMER_RESPONSE",
                "state": "unknown",
                "severity": "low",
                "weight_applied": 0.0,
                "score_contribution": 0.0,
                "explanation": "No customer reply activity records are available for this deal.",
                "why_it_matters": "Activity history is required to determine customer responsiveness.",
                "evidence_ids": []
            })
        else:
            known_signals_count += 1
            most_recent_dt = None
            recent_ref = None
            recent_text = None
            
            for a in customer_activities:
                occ = a.get("occurred_at")
                if occ:
                    if occ.tzinfo is None:
                        occ = occ.replace(tzinfo=timezone.utc)
                    if most_recent_dt is None or occ > most_recent_dt:
                        most_recent_dt = occ
                        recent_ref = a.get("source_ref", "ACT")
                        recent_text = a.get("detail", "")
                        
            for c in conversations:
                occ = c.get("occurred_at")
                if occ:
                    if occ.tzinfo is None:
                        occ = occ.replace(tzinfo=timezone.utc)
                    if most_recent_dt is None or occ > most_recent_dt:
                        most_recent_dt = occ
                        recent_ref = c.get("source_record_ref", "CONV")
                        recent_text = c.get("summary", "")

            if most_recent_dt is not None:
                days_since = (now - most_recent_dt).days
                if days_since > threshold_days:
                    weight = float(cfg_reply.get("weight", 20.0))
                    signals.append({
                        "signal_code": "NO_RECENT_CUSTOMER_RESPONSE",
                        "state": "detected",
                        "severity": "high",
                        "weight_applied": weight,
                        "score_contribution": weight,
                        "explanation": f"Last customer interaction was {days_since} days ago (threshold: {threshold_days} days).",
                        "why_it_matters": "Deals with prolonged silence suffer severe win-rate drop-off and higher buyer ghosting risk.",
                        "evidence_ids": [{
                            "source_ref": recent_ref,
                            "occurred_at": most_recent_dt.isoformat(),
                            "detail": recent_text
                        }]
                    })
                else:
                    signals.append({
                        "signal_code": "NO_RECENT_CUSTOMER_RESPONSE",
                        "state": "not_detected",
                        "severity": "low",
                        "weight_applied": 0.0,
                        "score_contribution": 0.0,
                        "explanation": f"Customer engaged {days_since} days ago, within the active {threshold_days}-day threshold.",
                        "why_it_matters": "Active engagement confirms ongoing stakeholder interest.",
                        "evidence_ids": []
                    })
            else:
                signals.append({
                    "signal_code": "NO_RECENT_CUSTOMER_RESPONSE",
                    "state": "not_detected",
                    "severity": "low",
                    "weight_applied": 0.0,
                    "score_contribution": 0.0,
                    "explanation": "Customer response records found and verified.",
                    "why_it_matters": "Customer dialogue is active.",
                    "evidence_ids": []
                })

    # 2. UNRESOLVED_PRICING_OBJECTION
    cfg_price = config.get("UNRESOLVED_PRICING_OBJECTION", DEFAULT_RISK_CONFIG["UNRESOLVED_PRICING_OBJECTION"])
    if cfg_price.get("enabled", True):
        known_signals_count += 1
        pricing_objections = [
            f for f in findings 
            if "pricing" in f.get("label", "").lower() and f.get("status") == "open"
        ]
        if pricing_objections:
            weight = float(cfg_price.get("weight", 25.0))
            ev_list = []
            for po in pricing_objections:
                ev_list.append({
                    "source_ref": po.get("source_ref", "FINDING"),
                    "label": po.get("label"),
                    "occurred_at": po.get("occurred_at", now.isoformat())
                })
            signals.append({
                "signal_code": "UNRESOLVED_PRICING_OBJECTION",
                "state": "detected",
                "severity": "critical",
                "weight_applied": weight,
                "score_contribution": weight,
                "explanation": f"{len(pricing_objections)} open pricing objection(s) without subsequent resolving evidence.",
                "why_it_matters": "Unresolved commercial pushback directly stalls close dates and jeopardizes deal margins.",
                "evidence_ids": ev_list
            })
        else:
            signals.append({
                "signal_code": "UNRESOLVED_PRICING_OBJECTION",
                "state": "not_detected",
                "severity": "low",
                "weight_applied": 0.0,
                "score_contribution": 0.0,
                "explanation": "No open pricing or commercial objections detected in records.",
                "why_it_matters": "Pricing terms are currently accepted or not contested.",
                "evidence_ids": []
            })

    # 3. REPEATED_POSTPONEMENT
    cfg_postpone = config.get("REPEATED_POSTPONEMENT", DEFAULT_RISK_CONFIG["REPEATED_POSTPONEMENT"])
    if cfg_postpone.get("enabled", True):
        known_signals_count += 1
        lookback = timedelta(days=cfg_postpone.get("lookback_days", 45))
        cutoff = now - lookback
        min_postpones = cfg_postpone.get("threshold_postpones", 2)
        
        postpone_activities = []
        for a in activities:
            if a.get("type") == "meeting_postponed":
                occ = a.get("occurred_at")
                if occ:
                    if occ.tzinfo is None:
                        occ = occ.replace(tzinfo=timezone.utc)
                    if occ >= cutoff:
                        postpone_activities.append(a)

        if len(postpone_activities) >= min_postpones:
            weight = float(cfg_postpone.get("weight", 15.0))
            ev_list = [{
                "source_ref": a.get("source_ref", "ACT"),
                "occurred_at": a.get("occurred_at").isoformat() if isinstance(a.get("occurred_at"), datetime) else str(a.get("occurred_at")),
                "detail": a.get("detail", "")
            } for a in postpone_activities]
            signals.append({
                "signal_code": "REPEATED_POSTPONEMENT",
                "state": "detected",
                "severity": "medium",
                "weight_applied": weight,
                "score_contribution": weight,
                "explanation": f"Customer postponed {len(postpone_activities)} scheduled meetings in the last {cfg_postpone.get('lookback_days', 45)} days.",
                "why_it_matters": "Multiple postponements indicate deprioritization, lack of budget authority, or waning momentum.",
                "evidence_ids": ev_list
            })
        else:
            signals.append({
                "signal_code": "REPEATED_POSTPONEMENT",
                "state": "not_detected",
                "severity": "low",
                "weight_applied": 0.0,
                "score_contribution": 0.0,
                "explanation": f"{len(postpone_activities)} postponements recorded (below threshold of {min_postpones}).",
                "why_it_matters": "Meeting cadences are progressing normally.",
                "evidence_ids": []
            })

    # 4. MISSING_NEXT_STEP
    cfg_next = config.get("MISSING_NEXT_STEP", DEFAULT_RISK_CONFIG["MISSING_NEXT_STEP"])
    if cfg_next.get("enabled", True):
        tracks_steps = deal_dict.get("source_tracks_next_steps", True)
        if not tracks_steps:
            # Source system does not track next steps -> Unknown!
            signals.append({
                "signal_code": "MISSING_NEXT_STEP",
                "state": "unknown",
                "severity": "low",
                "weight_applied": 0.0,
                "score_contribution": 0.0,
                "explanation": "CRM integration indicates this source system does not track next scheduled steps.",
                "why_it_matters": "Missing next step tracking cannot be verified as absent.",
                "evidence_ids": []
            })
        else:
            known_signals_count += 1
            next_act = deal_dict.get("next_activity_at")
            open_commitments = [
                f for f in findings 
                if f.get("kind") == "follow_up_commitment" and f.get("status") == "open"
            ]
            if next_act is None and not open_commitments:
                weight = float(cfg_next.get("weight", 15.0))
                signals.append({
                    "signal_code": "MISSING_NEXT_STEP",
                    "state": "detected",
                    "severity": "high",
                    "weight_applied": weight,
                    "score_contribution": weight,
                    "explanation": "No upcoming activity scheduled in CRM and no active follow-up commitments recorded.",
                    "why_it_matters": "Deals without a clear scheduled milestone stall or slip into unmonitored dormancy.",
                    "evidence_ids": [{
                        "source_ref": f"DEAL-{deal_dict.get('deal_code', deal_dict.get('id'))}",
                        "occurred_at": now.isoformat(),
                        "detail": "next_activity_at is null and no commitments documented."
                    }]
                })
            else:
                signals.append({
                    "signal_code": "MISSING_NEXT_STEP",
                    "state": "not_detected",
                    "severity": "low",
                    "weight_applied": 0.0,
                    "score_contribution": 0.0,
                    "explanation": "Confirmed next step or active follow-up commitment is in place.",
                    "why_it_matters": "Active next step maintains deal momentum.",
                    "evidence_ids": []
                })

    # 5. UNRESOLVED_PRODUCT_OR_IMPLEMENTATION_CONCERN
    cfg_tech = config.get("UNRESOLVED_PRODUCT_OR_IMPLEMENTATION_CONCERN", DEFAULT_RISK_CONFIG["UNRESOLVED_PRODUCT_OR_IMPLEMENTATION_CONCERN"])
    if cfg_tech.get("enabled", True):
        known_signals_count += 1
        tech_findings = [
            f for f in findings
            if f.get("status") == "open" and (
                "technical" in f.get("label", "").lower() or 
                "implementation" in f.get("label", "").lower() or 
                "product" in f.get("label", "").lower()
            )
        ]
        if tech_findings:
            weight = float(cfg_tech.get("weight", 15.0))
            ev_list = [{
                "source_ref": f.get("source_ref", "FINDING"),
                "label": f.get("label"),
                "occurred_at": f.get("occurred_at", now.isoformat())
            } for f in tech_findings]
            signals.append({
                "signal_code": "UNRESOLVED_PRODUCT_OR_IMPLEMENTATION_CONCERN",
                "state": "detected",
                "severity": "high",
                "weight_applied": weight,
                "score_contribution": weight,
                "explanation": f"{len(tech_findings)} open technical or implementation objection(s) logged.",
                "why_it_matters": "Technical roadblocks or onboarding friction prevent buyers from committing contractually.",
                "evidence_ids": ev_list
            })
        else:
            signals.append({
                "signal_code": "UNRESOLVED_PRODUCT_OR_IMPLEMENTATION_CONCERN",
                "state": "not_detected",
                "severity": "low",
                "weight_applied": 0.0,
                "score_contribution": 0.0,
                "explanation": "No unresolved product, technical, or implementation objections recorded.",
                "why_it_matters": "Technical validation is accepted or proceeding smoothly.",
                "evidence_ids": []
            })

    # 6. APPROACHING_DEADLINE
    cfg_deadline = config.get("APPROACHING_DEADLINE", DEFAULT_RISK_CONFIG["APPROACHING_DEADLINE"])
    if cfg_deadline.get("enabled", True):
        known_signals_count += 1
        threshold_days = cfg_deadline.get("threshold_days", 30)
        target_date = deal_dict.get("renewal_date") or deal_dict.get("expected_close_date")
        
        is_approaching = False
        days_until = None
        if target_date:
            if isinstance(target_date, str):
                from dateutil import parser
                target_date = parser.isoparse(target_date)
            if target_date.tzinfo is None:
                target_date = target_date.replace(tzinfo=timezone.utc)
            days_until = (target_date - now).days
            if 0 <= days_until <= threshold_days:
                is_approaching = True

        # Check if other high severity signal is detected or next step missing
        has_other_high_risk = any(
            s.get("state") == "detected" and s.get("severity") in ["high", "critical"]
            for s in signals
        )
        has_missing_next = any(
            s.get("signal_code") == "MISSING_NEXT_STEP" and s.get("state") == "detected"
            for s in signals
        )

        if is_approaching and (has_other_high_risk or has_missing_next):
            weight = float(cfg_deadline.get("weight", 15.0))
            signals.append({
                "signal_code": "APPROACHING_DEADLINE",
                "state": "detected",
                "severity": "high",
                "weight_applied": weight,
                "score_contribution": weight,
                "explanation": f"Close/Renewal deadline is {days_until} days away with unresolved risk factors detected.",
                "why_it_matters": "Approaching deadlines with active objections lead to last-minute slippage or forced concessions.",
                "evidence_ids": [{
                    "source_ref": f"DEAL-{deal_dict.get('deal_code', deal_dict.get('id'))}",
                    "occurred_at": target_date.isoformat(),
                    "detail": f"Target deadline {target_date.date()}, {days_until} days away."
                }]
            })
        else:
            signals.append({
                "signal_code": "APPROACHING_DEADLINE",
                "state": "not_detected",
                "severity": "low",
                "weight_applied": 0.0,
                "score_contribution": 0.0,
                "explanation": f"Deadline is {days_until if days_until is not None else 'unset'} days away; no high-risk deadline squeeze.",
                "why_it_matters": "Sufficient runway remains to resolve open discussion points.",
                "evidence_ids": []
            })

    # 7. REPEATED_CUSTOMER_CONCERN
    cfg_repeat = config.get("REPEATED_CUSTOMER_CONCERN", DEFAULT_RISK_CONFIG["REPEATED_CUSTOMER_CONCERN"])
    if cfg_repeat.get("enabled", True):
        known_signals_count += 1
        min_conv = cfg_repeat.get("min_conversations", 2)
        
        # Check if same objection kind raised across >= 2 separate conversations
        objection_conv_map = {}
        for f in findings:
            if f.get("kind") == "objection":
                label = f.get("label", "").lower()
                c_id = f.get("conversation_id", 0)
                if label not in objection_conv_map:
                    objection_conv_map[label] = set()
                objection_conv_map[label].add(c_id)

        repeated_labels = [lbl for lbl, c_set in objection_conv_map.items() if len(c_set) >= min_conv]
        if repeated_labels:
            weight = float(cfg_repeat.get("weight", 10.0))
            signals.append({
                "signal_code": "REPEATED_CUSTOMER_CONCERN",
                "state": "detected",
                "severity": "medium",
                "weight_applied": weight,
                "score_contribution": weight,
                "explanation": f"Customer repeated the same concern ({', '.join(repeated_labels)}) across multiple conversations.",
                "why_it_matters": "Persistent objections suggest the buyer feels unheard or previous answers were unsatisfactory.",
                "evidence_ids": [{
                    "source_ref": f"CONV-MULTI",
                    "occurred_at": now.isoformat(),
                    "detail": f"Raised in {len(objection_conv_map[repeated_labels[0]])} separate interactions."
                }]
            })
        else:
            signals.append({
                "signal_code": "REPEATED_CUSTOMER_CONCERN",
                "state": "not_detected",
                "severity": "low",
                "weight_applied": 0.0,
                "score_contribution": 0.0,
                "explanation": "No objection categories have been repeatedly voiced across multiple calls.",
                "why_it_matters": "Objections are either isolated or resolved quickly.",
                "evidence_ids": []
            })

    # 8. MISSING_DECISION_MAKER
    cfg_dm = config.get("MISSING_DECISION_MAKER", DEFAULT_RISK_CONFIG["MISSING_DECISION_MAKER"])
    if cfg_dm.get("enabled", True):
        dm_known = deal_dict.get("decision_maker_known")
        if dm_known is None:
            # Tri-state None -> Unknown! Missing info is not risk!
            signals.append({
                "signal_code": "MISSING_DECISION_MAKER",
                "state": "unknown",
                "severity": "low",
                "weight_applied": 0.0,
                "score_contribution": 0.0,
                "explanation": "Decision maker status has not been confirmed or documented in CRM records.",
                "why_it_matters": "Decision maker access cannot be determined without discovery records.",
                "evidence_ids": []
            })
        else:
            known_signals_count += 1
            if dm_known is False:
                weight = float(cfg_dm.get("weight", 10.0))
                signals.append({
                    "signal_code": "MISSING_DECISION_MAKER",
                    "state": "detected",
                    "severity": "medium",
                    "weight_applied": weight,
                    "score_contribution": weight,
                    "explanation": "CRM explicitly records that the economic decision maker has not been engaged.",
                    "why_it_matters": "Deals held exclusively with non-decision makers often fail procurement or budget sign-off.",
                    "evidence_ids": [{
                        "source_ref": f"DEAL-{deal_dict.get('deal_code', deal_dict.get('id'))}",
                        "occurred_at": now.isoformat(),
                        "detail": "decision_maker_known is explicitly false."
                    }]
                })
            else:
                signals.append({
                    "signal_code": "MISSING_DECISION_MAKER",
                    "state": "not_detected",
                    "severity": "low",
                    "weight_applied": 0.0,
                    "score_contribution": 0.0,
                    "explanation": "Key economic decision maker is engaged and identified.",
                    "why_it_matters": "Direct access to executive sponsors shortens buying cycles.",
                    "evidence_ids": []
                })

    # Compute total score & completeness
    raw_score = sum(s["score_contribution"] for s in signals if s["state"] == "detected")
    total_score = min(100.0, round(raw_score, 1))
    category = determine_risk_category(total_score)
    completeness_pct = round((known_signals_count / float(total_signals_evaluated)) * 100.0, 1)

    confidence_note = "High deterministic rule alignment"
    if completeness_pct < 75.0:
        confidence_note = "Partial risk visibility due to incomplete source tracking records"

    return {
        "score": total_score,
        "category": category,
        "data_completeness_pct": completeness_pct,
        "confidence_note": confidence_note,
        "signals": signals,
        "config_snapshot": config,
        "as_of": now.isoformat()
    }
