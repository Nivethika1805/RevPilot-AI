import io
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.entities import (
    Deal, Account, User, Conversation, Activity, ImportJob, ImportRowResult,
    FieldProvenance, FieldConflict, RiskAssessment
)
from app.services.audit_service import log_audit_event
from app.services.risk_engine import assess_deal_risk
from app.services.action_service import generate_deduped_actions_for_deal

# Expected columns and schema mappings
DEAL_FIELD_MAP = {
    "deal_code": ["deal_code", "code", "id", "deal_id"],
    "name": ["name", "deal_name", "title"],
    "account_name": ["account", "account_name", "company"],
    "value": ["value", "amount", "deal_value", "arr", "acv"],
    "stage": ["stage", "deal_stage", "status_stage"],
    "status": ["status", "deal_status"],
    "owner_email": ["owner", "owner_email", "rep_email", "rep"],
    "expected_close_date": ["close_date", "expected_close_date", "target_close"],
    "renewal_date": ["renewal_date", "renewal"],
    "next_activity_at": ["next_activity", "next_activity_at", "next_step_date"],
    "source_tracks_next_steps": ["tracks_next_steps", "source_tracks_next_steps"],
    "decision_maker_known": ["decision_maker_known", "has_decision_maker"]
}

def compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def compute_row_hash(row_dict: Dict[str, Any]) -> str:
    # Deterministic string representation of normalized key-values
    normalized_items = []
    for k in sorted(row_dict.keys()):
        val = row_dict[k]
        if val is None or pd.isna(val):
            s_val = ""
        else:
            s_val = str(val).strip().lower()
        normalized_items.append(f"{k}:{s_val}")
    raw_str = "|".join(normalized_items)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

def suggest_column_mapping(columns: List[str], entity_type: str = "deal") -> Dict[str, str]:
    mapping = {}
    col_lower_map = {c.lower().strip().replace(" ", "_"): c for c in columns}
    field_rules = DEAL_FIELD_MAP

    for target_field, aliases in field_rules.items():
        for alias in aliases:
            if alias in col_lower_map:
                mapping[col_lower_map[alias]] = target_field
                break
    return mapping

def parse_and_validate_file(content: bytes, filename: str) -> Tuple[pd.DataFrame, str]:
    if len(content) > 5 * 1024 * 1024:
        raise ValueError("File exceeds maximum allowed size of 5 MB.")

    fmt = "csv"
    if filename.endswith(".json") or filename.endswith(".JSON"):
        fmt = "json"
        try:
            data = json.loads(content.decode("utf-8"))
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict) and "records" in data:
                df = pd.DataFrame(data["records"])
            else:
                df = pd.DataFrame([data])
        except Exception as e:
            raise ValueError(f"Malformed JSON file: {str(e)}")
    else:
        if b"\x00" in content:
            raise ValueError("Malformed CSV file: binary or null byte sequence detected.")
        try:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8", on_bad_lines="error")
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(io.BytesIO(content), encoding="latin1", on_bad_lines="error")
            except Exception as e:
                raise ValueError(f"Malformed CSV file encoding: {str(e)}")
        except Exception as e:
            raise ValueError(f"Malformed CSV file syntax: {str(e)}")

    if df.empty:
        raise ValueError("Uploaded file contains no rows.")
    if len(df) > 5000:
        raise ValueError("File exceeds 5,000 rows limit.")

    return df, fmt

def plan_import(
    db: Session,
    job: ImportJob,
    df: pd.DataFrame,
    column_mapping: Dict[str, str]
) -> Dict[str, Any]:
    """
    Simulates row-level classification:
    - new
    - changed
    - unchanged
    - conflict
    - invalid
    - duplicate_in_file
    """
    seen_in_file_keys = set()
    summary = {
        "new": 0,
        "changed": 0,
        "unchanged": 0,
        "conflict": 0,
        "invalid": 0,
        "skipped": 0,
        "duplicate_in_file": 0
    }
    row_plans = []
    validation_errors = []

    for idx, raw_row in df.iterrows():
        row_num = idx + 1
        row_data = {}
        for src_col, target_field in column_mapping.items():
            if src_col in raw_row:
                val = raw_row[src_col]
                row_data[target_field] = None if pd.isna(val) else val

        row_hash = compute_row_hash(row_data)

        # Validation of required fields
        errors = []
        deal_code = row_data.get("deal_code")
        if not deal_code:
            # Fallback to name
            if not row_data.get("name"):
                errors.append("Missing required field: deal_code or name")
        
        if errors:
            summary["invalid"] += 1
            validation_errors.append({"row": row_num, "errors": errors})
            row_plans.append({
                "row_number": row_num,
                "external_key": str(deal_code) if deal_code else f"ROW-{row_num}",
                "outcome": "invalid",
                "match_method": "none",
                "errors": errors,
                "changes": {},
                "row_hash": row_hash
            })
            continue

        deal_code_str = str(deal_code).strip()
        if deal_code_str in seen_in_file_keys:
            summary["duplicate_in_file"] += 1
            row_plans.append({
                "row_number": row_num,
                "external_key": deal_code_str,
                "outcome": "duplicate_in_file",
                "match_method": "external_id",
                "errors": ["Duplicate key found within the same import file."],
                "changes": {},
                "row_hash": row_hash
            })
            continue
        seen_in_file_keys.add(deal_code_str)

        # Match against database
        existing_deal = db.query(Deal).filter(
            or_(Deal.deal_code == deal_code_str, Deal.external_id == deal_code_str)
        ).first()

        if not existing_deal:
            # Try natural key match
            acc_name = str(row_data.get("account_name", "")).strip().lower()
            d_name = str(row_data.get("name", "")).strip().lower()
            if acc_name and d_name:
                candidates = db.query(Deal).join(Account).filter(
                    Account.normalized_name == acc_name,
                    Deal.name.ilike(d_name)
                ).all()
                if len(candidates) == 1:
                    existing_deal = candidates[0]
                elif len(candidates) > 1:
                    # Ambiguous natural key match! Mark as conflict/needs review
                    summary["conflict"] += 1
                    row_plans.append({
                        "row_number": row_num,
                        "external_key": deal_code_str,
                        "outcome": "conflict",
                        "match_method": "natural_key",
                        "errors": [f"Ambiguous match: {len(candidates)} deals match natural key."],
                        "changes": {},
                        "row_hash": row_hash
                    })
                    continue

        if not existing_deal:
            summary["new"] += 1
            row_plans.append({
                "row_number": row_num,
                "external_key": deal_code_str,
                "outcome": "new",
                "match_method": "none",
                "errors": [],
                "changes": {k: {"before": None, "after": str(v)} for k, v in row_data.items() if v is not None},
                "row_hash": row_hash
            })
            continue

        # Check existing fields vs incoming
        changes = {}
        has_conflict = False
        tracked_fields = ["name", "value", "stage", "status"]

        for f_name in tracked_fields:
            if f_name in row_data and row_data[f_name] is not None:
                inc_val = str(row_data[f_name]).strip()
                curr_val = str(getattr(existing_deal, f_name, "")).strip()

                # Check provenance
                prov = db.query(FieldProvenance).filter(
                    FieldProvenance.entity_type == "deal",
                    FieldProvenance.entity_id == existing_deal.id,
                    FieldProvenance.field_name == f_name
                ).first()

                if prov and prov.is_overridden:
                    # Manual override policy
                    if inc_val == prov.source_value:
                        # Case c: Source didn't change -> silent preserve
                        pass
                    elif inc_val == curr_val:
                        # Case e: Source matches current manual -> auto-agree
                        changes[f_name] = {"action": "auto_agree", "current": curr_val, "incoming": inc_val}
                    else:
                        # Case d: Source changed and conflicts with manual value
                        has_conflict = True
                        changes[f_name] = {
                            "action": "conflict",
                            "current_manual": curr_val,
                            "incoming_source": inc_val,
                            "baseline": prov.source_value
                        }
                else:
                    # Normal field
                    if inc_val != curr_val:
                        changes[f_name] = {"before": curr_val, "after": inc_val}

        if has_conflict:
            summary["conflict"] += 1
            outcome = "conflict"
        elif changes:
            summary["changed"] += 1
            outcome = "changed"
        else:
            summary["unchanged"] += 1
            outcome = "unchanged"

        row_plans.append({
            "row_number": row_num,
            "external_key": deal_code_str,
            "outcome": outcome,
            "match_method": "external_id",
            "errors": [],
            "changes": changes,
            "row_hash": row_hash
        })

    return {
        "summary": summary,
        "row_plans": row_plans,
        "validation_errors": validation_errors
    }

def execute_confirmed_import(
    db: Session,
    job_id: int,
    column_mapping: Dict[str, str],
    df: pd.DataFrame,
    skip_invalid: bool,
    now: datetime
) -> Dict[str, Any]:
    """
    Executes import inside a single atomic transaction.
    Re-assesses affected deals deterministically.
    """
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        raise ValueError("Import job not found")

    plan = plan_import(db, job, df, column_mapping)
    row_plans = plan["row_plans"]

    affected_deal_ids = set()

    for r_plan in row_plans:
        outcome = r_plan["outcome"]
        row_num = r_plan["row_number"]
        deal_code_str = r_plan["external_key"]

        # Save ImportRowResult
        row_res = ImportRowResult(
            job_id=job.id,
            row_number=row_num,
            external_key=deal_code_str,
            match_method=r_plan["match_method"],
            outcome=outcome,
            errors=r_plan["errors"],
            changes=r_plan["changes"],
            row_hash=r_plan["row_hash"]
        )
        db.add(row_res)

        if outcome in ["invalid", "duplicate_in_file", "skipped"]:
            continue

        raw_row = df.iloc[row_num - 1]
        row_data = {}
        for src_col, target_field in column_mapping.items():
            if src_col in raw_row:
                val = raw_row[src_col]
                row_data[target_field] = None if pd.isna(val) else val

        if outcome == "new":
            # Account lookup or create
            acc_name = str(row_data.get("account_name", "Demo Account")).strip()
            norm_name = acc_name.lower()
            acc = db.query(Account).filter(Account.normalized_name == norm_name).first()
            if not acc:
                acc = Account(name=acc_name, normalized_name=norm_name, synthetic_flag=True)
                db.add(acc)
                db.flush()

            # Deal create
            val = float(row_data.get("value", 0.0)) if row_data.get("value") is not None else 0.0
            new_deal = Deal(
                deal_code=deal_code_str,
                external_id=deal_code_str,
                account_id=acc.id,
                name=str(row_data.get("name", f"Deal {deal_code_str}")).strip(),
                value=val,
                currency="USD",
                stage=str(row_data.get("stage", "Discovery")).strip(),
                status=str(row_data.get("status", "open")).strip(),
                source_tracks_next_steps=True
            )
            db.add(new_deal)
            db.flush()

            # Initialize field provenance for new deal
            for f_name in ["name", "value", "stage", "status"]:
                v = str(getattr(new_deal, f_name, ""))
                prov = FieldProvenance(
                    entity_type="deal",
                    entity_id=new_deal.id,
                    field_name=f_name,
                    source_value=v,
                    current_value=v,
                    is_overridden=False,
                    last_update_source="import",
                    last_import_job_id=job.id
                )
                db.add(prov)

            log_audit_event(
                db,
                event_type="deal_imported_new",
                entity_type="deal",
                entity_id=new_deal.id,
                actor_label="Import Wizard",
                after={"deal_code": deal_code_str, "value": val},
                import_job_id=job.id
            )
            affected_deal_ids.add(new_deal.id)

        elif outcome in ["changed", "conflict", "unchanged"]:
            deal = db.query(Deal).filter(
                or_(Deal.deal_code == deal_code_str, Deal.external_id == deal_code_str)
            ).first()

            if deal and outcome != "unchanged":
                # Apply changes with provenance checks
                before_state = {"value": deal.value, "stage": deal.stage, "name": deal.name}
                tracked_fields = ["name", "value", "stage", "status"]

                for f_name in tracked_fields:
                    if f_name in row_data and row_data[f_name] is not None:
                        inc_val = str(row_data[f_name]).strip()
                        curr_val = str(getattr(deal, f_name, "")).strip()

                        prov = db.query(FieldProvenance).filter(
                            FieldProvenance.entity_type == "deal",
                            FieldProvenance.entity_id == deal.id,
                            FieldProvenance.field_name == f_name
                        ).first()

                        if not prov:
                            prov = FieldProvenance(
                                entity_type="deal",
                                entity_id=deal.id,
                                field_name=f_name,
                                source_value=curr_val,
                                current_value=curr_val,
                                is_overridden=False,
                                last_update_source="seed"
                            )
                            db.add(prov)
                            db.flush()

                        if prov.is_overridden:
                            if inc_val == prov.source_value:
                                # Case c: Silent preserve
                                pass
                            elif inc_val == curr_val:
                                # Case e: Auto-agree
                                prov.is_overridden = False
                                prov.source_value = inc_val
                                prov.last_update_source = "import"
                                prov.last_import_job_id = job.id
                            else:
                                # Case d: CONFLICT!
                                conflict = FieldConflict(
                                    entity_type="deal",
                                    entity_id=deal.id,
                                    field_name=f_name,
                                    current_value=curr_val,
                                    incoming_value=inc_val,
                                    source_baseline_value=prov.source_value,
                                    import_job_id=job.id,
                                    status="pending"
                                )
                                db.add(conflict)
                        else:
                            if inc_val != curr_val:
                                # Case a: Normal update
                                if f_name == "value":
                                    deal.value = float(inc_val)
                                elif f_name == "stage":
                                    deal.stage = inc_val
                                elif f_name == "name":
                                    deal.name = inc_val
                                elif f_name == "status":
                                    deal.status = inc_val

                                prov.previous_source_value = prov.source_value
                                prov.source_value = inc_val
                                prov.current_value = inc_val
                                prov.last_update_source = "import"
                                prov.last_import_job_id = job.id

                log_audit_event(
                    db,
                    event_type="deal_imported_update",
                    entity_type="deal",
                    entity_id=deal.id,
                    actor_label="Import Wizard",
                    before=before_state,
                    after={"value": deal.value, "stage": deal.stage, "name": deal.name},
                    import_job_id=job.id
                )
                affected_deal_ids.add(deal.id)

    job.status = "completed"
    job.summary = plan["summary"]
    job.completed_at = now
    
    log_audit_event(
        db,
        event_type="import_completed",
        entity_type="import_job",
        entity_id=job.id,
        actor_label="Import Wizard",
        after=plan["summary"],
        import_job_id=job.id
    )

    db.flush()

    # Re-run risk assessment for affected deals
    for d_id in affected_deal_ids:
        d = db.query(Deal).filter(Deal.id == d_id).first()
        if d:
            convs = [c.__dict__ for c in d.conversations]
            acts = [a.__dict__ for a in d.activities]
            f_list = []
            for c in d.conversations:
                for f in c.findings:
                    f_dict = f.__dict__.copy()
                    if f.evidence:
                        f_dict["source_ref"] = f.evidence.source_ref
                    f_list.append(f_dict)
            
            assessment_res = assess_deal_risk(d.__dict__, convs, f_list, acts, now=now)
            
            # Archive previous
            db.query(RiskAssessment).filter(
                RiskAssessment.deal_id == d.id,
                RiskAssessment.is_current == True
            ).update({"is_current": False})

            from app.models.entities import RiskSignal
            new_assessment = RiskAssessment(
                deal_id=d.id,
                assessed_at=now,
                as_of=now,
                rules_version=1,
                config_snapshot=assessment_res["config_snapshot"],
                score=assessment_res["score"],
                category=assessment_res["category"],
                data_completeness_pct=assessment_res["data_completeness_pct"],
                confidence_note=assessment_res["confidence_note"],
                trigger="import",
                is_current=True
            )
            db.add(new_assessment)
            db.flush()

            for s_data in assessment_res["signals"]:
                sig = RiskSignal(
                    assessment_id=new_assessment.id,
                    signal_code=s_data["signal_code"],
                    state=s_data["state"],
                    severity=s_data["severity"],
                    weight_applied=s_data["weight_applied"],
                    score_contribution=s_data["score_contribution"],
                    explanation=s_data["explanation"],
                    why_it_matters=s_data["why_it_matters"],
                    evidence_ids=s_data.get("evidence_ids", [])
                )
                db.add(sig)

            # Generate deduped recommended actions
            generate_deduped_actions_for_deal(db, d, new_assessment, now)

    return plan["summary"]
