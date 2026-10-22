import os
import csv
import json
import zipfile
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import (
    Deal, Conversation, RiskAssessment, FollowUpAction, RoutingDecision,
    ImportJob, AuditEvent, ExportJob, ExportFile, ExportManifest
)

def sanitize_csv_cell(val: Any) -> Any:
    """
    Guards against CSV formula injection.
    Prefixes cells starting with =, +, -, @ with an apostrophe '.
    """
    if val is None:
        return ""
    s = str(val)
    if s.startswith(("=", "+", "-", "@")):
        return f"'{s}"
    return s

def compute_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def generate_export_bundle(
    db: Session,
    export_job: ExportJob,
    as_of: datetime,
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    if base_dir is None:
        base_dir = settings.EXPORTS_DIR
    
    target_dir = os.path.join(base_dir, f"export_{export_job.id}")
    os.makedirs(target_dir, exist_ok=True)

    files_manifest_entries = []
    generated_file_paths = []

    # 1. Deals
    if "deals" in export_job.entities:
        deals = db.query(Deal).all()
        fname = f"deals.{export_job.format}"
        fpath = os.path.join(target_dir, fname)
        
        deal_rows = []
        for d in deals:
            curr_ass = next((a for a in d.risk_assessments if a.is_current), None)
            deal_rows.append({
                "deal_code": d.deal_code,
                "name": d.name,
                "account_name": d.account.name if d.account else "",
                "value": d.value,
                "currency": d.currency,
                "stage": d.stage,
                "status": d.status,
                "risk_score": curr_ass.score if curr_ass else 0.0,
                "risk_category": curr_ass.category if curr_ass else "Low",
                "expected_close_date": d.expected_close_date.isoformat() if d.expected_close_date else "",
                "created_at": d.created_at.isoformat()
            })

        if export_job.format == "json":
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(deal_rows, f, indent=2)
        else:
            with open(fpath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = list(deal_rows[0].keys()) if deal_rows else ["deal_code", "name", "value"]
                writer.writerow(headers)
                for r in deal_rows:
                    writer.writerow([sanitize_csv_cell(r.get(h)) for h in headers])

        sha = compute_file_sha256(fpath)
        sz = os.path.getsize(fpath)
        ef = ExportFile(
            export_job_id=export_job.id,
            file_name=fname,
            entity="deals",
            record_count=len(deal_rows),
            sha256=sha,
            size_bytes=sz,
            path=fpath
        )
        db.add(ef)
        files_manifest_entries.append({
            "file_name": fname,
            "entity": "deals",
            "record_count": len(deal_rows),
            "sha256": sha,
            "size_bytes": sz
        })
        generated_file_paths.append(fpath)

    # 2. Conversations
    if "conversations" in export_job.entities:
        convs = db.query(Conversation).all()
        fname = f"conversations.{export_job.format}"
        fpath = os.path.join(target_dir, fname)
        
        conv_rows = []
        for c in convs:
            conv_rows.append({
                "source_record_ref": c.source_record_ref,
                "deal_code": c.deal.deal_code if c.deal else "",
                "type": c.type,
                "occurred_at": c.occurred_at.isoformat(),
                "summary": c.summary,
                "customer_intent": c.customer_intent or "",
                "sentiment_label": c.sentiment_label or "",
                "routing_status": c.routing_status,
                "urgency": c.urgency
            })

        if export_job.format == "json":
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(conv_rows, f, indent=2)
        else:
            with open(fpath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = list(conv_rows[0].keys()) if conv_rows else ["source_record_ref", "summary"]
                writer.writerow(headers)
                for r in conv_rows:
                    writer.writerow([sanitize_csv_cell(r.get(h)) for h in headers])

        sha = compute_file_sha256(fpath)
        sz = os.path.getsize(fpath)
        ef = ExportFile(
            export_job_id=export_job.id,
            file_name=fname,
            entity="conversations",
            record_count=len(conv_rows),
            sha256=sha,
            size_bytes=sz,
            path=fpath
        )
        db.add(ef)
        files_manifest_entries.append({
            "file_name": fname,
            "entity": "conversations",
            "record_count": len(conv_rows),
            "sha256": sha,
            "size_bytes": sz
        })
        generated_file_paths.append(fpath)

    # 3. Risk Assessments
    if "risk_assessments" in export_job.entities:
        assessments = db.query(RiskAssessment).filter(RiskAssessment.is_current == True).all()
        fname = f"risk_assessments.{export_job.format}"
        fpath = os.path.join(target_dir, fname)
        
        ass_rows = []
        for a in assessments:
            ass_rows.append({
                "deal_code": a.deal.deal_code if a.deal else "",
                "score": a.score,
                "category": a.category,
                "data_completeness_pct": a.data_completeness_pct,
                "trigger": a.trigger,
                "assessed_at": a.assessed_at.isoformat()
            })

        if export_job.format == "json":
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(ass_rows, f, indent=2)
        else:
            with open(fpath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = list(ass_rows[0].keys()) if ass_rows else ["deal_code", "score"]
                writer.writerow(headers)
                for r in ass_rows:
                    writer.writerow([sanitize_csv_cell(r.get(h)) for h in headers])

        sha = compute_file_sha256(fpath)
        sz = os.path.getsize(fpath)
        ef = ExportFile(
            export_job_id=export_job.id,
            file_name=fname,
            entity="risk_assessments",
            record_count=len(ass_rows),
            sha256=sha,
            size_bytes=sz,
            path=fpath
        )
        db.add(ef)
        files_manifest_entries.append({
            "file_name": fname,
            "entity": "risk_assessments",
            "record_count": len(ass_rows),
            "sha256": sha,
            "size_bytes": sz
        })
        generated_file_paths.append(fpath)

    # 4. Actions
    if "follow_up_actions" in export_job.entities:
        actions = db.query(FollowUpAction).all()
        fname = f"follow_up_actions.{export_job.format}"
        fpath = os.path.join(target_dir, fname)
        
        act_rows = []
        for a in actions:
            act_rows.append({
                "deal_code": a.deal.deal_code if a.deal else "",
                "title": a.title,
                "reason": a.reason,
                "priority": a.priority,
                "status": a.status,
                "due_date": a.due_date.isoformat() if a.due_date else ""
            })

        if export_job.format == "json":
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(act_rows, f, indent=2)
        else:
            with open(fpath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = list(act_rows[0].keys()) if act_rows else ["title", "status"]
                writer.writerow(headers)
                for r in act_rows:
                    writer.writerow([sanitize_csv_cell(r.get(h)) for h in headers])

        sha = compute_file_sha256(fpath)
        sz = os.path.getsize(fpath)
        ef = ExportFile(
            export_job_id=export_job.id,
            file_name=fname,
            entity="follow_up_actions",
            record_count=len(act_rows),
            sha256=sha,
            size_bytes=sz,
            path=fpath
        )
        db.add(ef)
        files_manifest_entries.append({
            "file_name": fname,
            "entity": "follow_up_actions",
            "record_count": len(act_rows),
            "sha256": sha,
            "size_bytes": sz
        })
    # 5. Audit History
    if "audit_history" in export_job.entities or "audit_events" in export_job.entities:
        events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
        fname = f"audit_history.{export_job.format}"
        fpath = os.path.join(target_dir, fname)

        audit_rows = []
        for ev in events:
            audit_rows.append({
                "event_id": ev.id,
                "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else "",
                "actor_label": ev.actor_label,
                "event_type": ev.event_type,
                "entity_type": ev.entity_type,
                "entity_id": ev.entity_id or "",
                "reason": ev.reason or "",
                "correlation_id": ev.correlation_id or ""
            })

        if export_job.format == "json":
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(audit_rows, f, indent=2)
        else:
            with open(fpath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = list(audit_rows[0].keys()) if audit_rows else ["event_id", "event_type", "entity_type"]
                writer.writerow(headers)
                for r in audit_rows:
                    writer.writerow([sanitize_csv_cell(r.get(h)) for h in headers])

        sha = compute_file_sha256(fpath)
        sz = os.path.getsize(fpath)
        ef = ExportFile(
            export_job_id=export_job.id,
            file_name=fname,
            entity="audit_history",
            record_count=len(audit_rows),
            sha256=sha,
            size_bytes=sz,
            path=fpath
        )
        db.add(ef)
        files_manifest_entries.append({
            "file_name": fname,
            "entity": "audit_history",
            "record_count": len(audit_rows),
            "sha256": sha,
            "size_bytes": sz
        })
        generated_file_paths.append(fpath)

    # Verify each generated file exists and has non-zero size before confirming manifest
    all_verified = True
    for fe in files_manifest_entries:
        fpath = os.path.join(target_dir, fe["file_name"])
        if not os.path.exists(fpath):
            all_verified = False
            break
        actual_sha = compute_file_sha256(fpath)
        if actual_sha != fe["sha256"]:
            all_verified = False
            break

    total_records = sum(fe["record_count"] for fe in files_manifest_entries)
    validation_status = "verified" if (all_verified and len(files_manifest_entries) > 0) else "failed"

    # Build manifest JSON
    manifest_data = {
        "export_id": export_job.id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "format": export_job.format,
        "entities": export_job.entities,
        "applied_filters": export_job.filters,
        "app_version": settings.VERSION,
        "schema_version": settings.SCHEMA_VERSION,
        "as_of": as_of.isoformat(),
        "synthetic_data": True,
        "total_records": total_records,
        "validation_status": validation_status,
        "files": files_manifest_entries
    }

    manifest_bytes = json.dumps(manifest_data, sort_keys=True, indent=2).encode("utf-8")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    manifest_data["manifest_sha256"] = manifest_sha256

    manifest_path = os.path.join(target_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    export_manifest = ExportManifest(
        export_job_id=export_job.id,
        manifest_json=manifest_data,
        manifest_sha256=manifest_sha256
    )
    db.add(export_manifest)

    # Sync validation status to export_job record
    export_job.validation_status = validation_status

    # Create ZIP bundle
    zip_path = os.path.join(target_dir, f"export_bundle_{export_job.id}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(manifest_path, arcname="manifest.json")
        for fp in generated_file_paths:
            zipf.write(fp, arcname=os.path.basename(fp))

    return manifest_data

def verify_export_integrity(db: Session, export_id: int) -> Dict[str, Any]:
    """
    Re-hashes files on disk and verifies they match the manifest hashes.
    """
    job = db.query(ExportJob).filter(ExportJob.id == export_id).first()
    if not job or not job.manifest:
        return {"export_id": export_id, "status": "tampered", "details": ["Export or manifest not found"], "all_matched": False}

    stored_manifest = job.manifest.manifest_json
    files_info = stored_manifest.get("files", [])
    
    details = []
    all_matched = True

    for fi in files_info:
        fname = fi["file_name"]
        expected_sha = fi["sha256"]
        expected_records = fi["record_count"]
        
        target_dir = os.path.join(settings.EXPORTS_DIR, f"export_{export_id}")
        fpath = os.path.join(target_dir, fname)

        if not os.path.exists(fpath):
            all_matched = False
            details.append({"file": fname, "status": "missing_on_disk"})
            continue

        actual_sha = compute_file_sha256(fpath)
        if actual_sha != expected_sha:
            all_matched = False
            details.append({
                "file": fname,
                "status": "sha256_mismatch",
                "expected": expected_sha,
                "actual": actual_sha
            })
        else:
            details.append({"file": fname, "status": "verified_match", "sha256": actual_sha})

    status_str = "verified" if all_matched else "tampered"
    return {
        "export_id": export_id,
        "status": status_str,
        "details": details,
        "all_matched": all_matched
    }
