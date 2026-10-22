import io
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.clock import get_clock
from app.models.entities import ImportJob, ImportRowResult, FieldProvenance, FieldConflict, Deal
from app.schemas.schemas import (
    ImportUploadResponse, ImportPlanRequest, ImportPlanResponse,
    ImportConfirmRequest, ImportReportResponse, FieldConflictRead,
    ConflictResolveRequest, FieldProvenanceRead
)
from app.services.import_service import (
    compute_file_hash, parse_and_validate_file, suggest_column_mapping,
    plan_import, execute_confirmed_import
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/imports", tags=["Import & Correction Lab"])

# In-memory storage for uploaded file bytes between upload & confirm (keyed by job_id)
_UPLOADED_CACHE: Dict[int, bytes] = {}

@router.post("/upload", response_model=ImportUploadResponse)
async def upload_import_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        df, fmt = parse_and_validate_file(content, file.filename or "import.csv")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    file_hash = compute_file_hash(content)
    size_bytes = len(content)

    suggested_mapping = suggest_column_mapping(df.columns.tolist(), entity_type="deal")

    clock = get_clock()
    now = clock.now()

    job = ImportJob(
        entity_type="deal",
        filename=file.filename or f"import_{int(now.timestamp())}.csv",
        file_sha256=file_hash,
        format=fmt,
        size_bytes=size_bytes,
        status="uploaded",
        column_mapping=suggested_mapping,
        summary={"total_rows": len(df)},
        created_at=now
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _UPLOADED_CACHE[job.id] = content

    preview_records = df.head(10).fillna("").to_dict(orient="records")

    return {
        "job_id": job.id,
        "filename": job.filename,
        "file_sha256": job.file_sha256,
        "format": fmt,
        "size_bytes": size_bytes,
        "suggested_entity_type": "deal",
        "total_rows": len(df),
        "columns_found": df.columns.tolist(),
        "suggested_mapping": suggested_mapping,
        "preview_rows": preview_records
    }

@router.post("/plan", response_model=ImportPlanResponse)
def generate_import_plan(
    req: ImportPlanRequest,
    db: Session = Depends(get_db)
):
    job = db.query(ImportJob).filter(ImportJob.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    content = _UPLOADED_CACHE.get(job.id)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file content expired. Please upload file again.")

    df, _ = parse_and_validate_file(content, job.filename)
    job.column_mapping = req.column_mapping
    job.entity_type = req.entity_type
    job.status = "previewed"
    db.commit()

    plan_res = plan_import(db, job, df, req.column_mapping)

    diff_preview = []
    for r in plan_res["row_plans"][:15]:
        if r["outcome"] in ["new", "changed", "conflict"]:
            diff_preview.append({
                "row_number": r["row_number"],
                "key": r["external_key"],
                "outcome": r["outcome"],
                "changes": r["changes"]
            })

    return {
        "job_id": job.id,
        "entity_type": req.entity_type,
        "summary": plan_res["summary"],
        "diff_preview": diff_preview,
        "validation_errors": plan_res["validation_errors"]
    }

@router.post("/confirm", response_model=ImportReportResponse)
def confirm_import(
    req: ImportConfirmRequest,
    db: Session = Depends(get_db)
):
    job = db.query(ImportJob).filter(ImportJob.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    content = _UPLOADED_CACHE.get(job.id)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file session expired. Please re-upload.")

    df, _ = parse_and_validate_file(content, job.filename)

    clock = get_clock()
    now = clock.now()

    try:
        summary = execute_confirmed_import(
            db=db,
            job_id=job.id,
            column_mapping=job.column_mapping or {},
            df=df,
            skip_invalid=req.skip_invalid_rows,
            now=now
        )
        db.commit()
    except Exception as e:
        db.rollback()
        job.status = "failed"
        log_audit_event(
            db,
            event_type="import_failed_rollback",
            entity_type="import_job",
            entity_id=job.id,
            actor_label="System",
            reason=f"Import transaction rolled back due to error: {str(e)}"
        )
        db.commit()
        raise HTTPException(status_code=500, detail=f"Import failed and rolled back cleanly: {str(e)}")

    return {
        "job_id": job.id,
        "filename": job.filename,
        "status": job.status,
        "summary": summary,
        "completed_at": job.completed_at,
        "error_count": summary.get("invalid", 0) + summary.get("duplicate_in_file", 0)
    }

@router.get("/{id}/report")
def get_import_report(id: int, db: Session = Depends(get_db)):
    job = db.query(ImportJob).filter(ImportJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    row_results = db.query(ImportRowResult).filter(ImportRowResult.job_id == id).all()

    return {
        "job_id": job.id,
        "filename": job.filename,
        "file_sha256": job.file_sha256,
        "status": job.status,
        "summary": job.summary,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "row_count": len(row_results),
        "rows": [{
            "row_number": r.row_number,
            "key": r.external_key,
            "outcome": r.outcome,
            "match_method": r.match_method,
            "errors": r.errors,
            "changes": r.changes
        } for r in row_results]
    }

@router.get("/{id}/errors.csv")
def download_errors_csv(id: int, db: Session = Depends(get_db)):
    job = db.query(ImportJob).filter(ImportJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    err_rows = db.query(ImportRowResult).filter(
        ImportRowResult.job_id == id,
        ImportRowResult.outcome.in_(["invalid", "duplicate_in_file", "conflict"])
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["row_number", "external_key", "outcome", "errors"])
    for r in err_rows:
        writer.writerow([r.row_number, r.external_key, r.outcome, "; ".join(r.errors or [])])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=import_errors_{id}.csv"}
    )

@router.get("/conflicts", response_model=List[FieldConflictRead])
def list_pending_conflicts(db: Session = Depends(get_db)):
    conflicts = db.query(FieldConflict).filter(FieldConflict.status == "pending").all()
    results = []
    for cf in conflicts:
        deal = db.query(Deal).filter(Deal.id == cf.entity_id).first() if cf.entity_type == "deal" else None
        label = f"{deal.deal_code} ({deal.name})" if deal else f"Entity #{cf.entity_id}"

        results.append({
            "id": cf.id,
            "entity_type": cf.entity_type,
            "entity_id": cf.entity_id,
            "entity_label": label,
            "field_name": cf.field_name,
            "current_value": cf.current_value,
            "incoming_value": cf.incoming_value,
            "source_baseline_value": cf.source_baseline_value,
            "import_job_id": cf.import_job_id,
            "status": cf.status,
            "resolved_by": cf.resolved_by,
            "resolved_at": cf.resolved_at,
            "resolution_value": cf.resolution_value,
            "created_at": cf.created_at
        })
    return results

@router.post("/conflicts/{id}/resolve")
def resolve_conflict(
    id: int,
    req: ConflictResolveRequest,
    db: Session = Depends(get_db)
):
    cf = db.query(FieldConflict).filter(FieldConflict.id == id).first()
    if not cf:
        raise HTTPException(status_code=404, detail="Conflict record not found")

    clock = get_clock()
    now = clock.now()

    choice = req.resolution_choice
    final_val = cf.current_value

    prov = db.query(FieldProvenance).filter(
        FieldProvenance.entity_type == cf.entity_type,
        FieldProvenance.entity_id == cf.entity_id,
        FieldProvenance.field_name == cf.field_name
    ).first()

    deal = db.query(Deal).filter(Deal.id == cf.entity_id).first() if cf.entity_type == "deal" else None

    if choice == "keep_manual":
        cf.status = "kept_manual"
        cf.resolution_value = cf.current_value
        if prov:
            prov.source_value = cf.incoming_value  # acknowledge new source baseline
            prov.is_overridden = True
            prov.last_update_source = "resolution"
            prov.updated_at = now

    elif choice == "accept_source":
        cf.status = "accepted_source"
        cf.resolution_value = cf.incoming_value
        final_val = cf.incoming_value
        if deal:
            if cf.field_name == "value":
                deal.value = float(cf.incoming_value)
            else:
                setattr(deal, cf.field_name, cf.incoming_value)
            deal.updated_at = now

        if prov:
            prov.source_value = cf.incoming_value
            prov.current_value = cf.incoming_value
            prov.is_overridden = False
            prov.last_update_source = "resolution"
            prov.updated_at = now

    elif choice == "custom_value":
        if not req.custom_value:
            raise HTTPException(status_code=400, detail="custom_value is required for custom_value resolution")
        cf.status = "custom_value"
        cf.resolution_value = req.custom_value
        final_val = req.custom_value
        if deal:
            if cf.field_name == "value":
                deal.value = float(req.custom_value)
            else:
                setattr(deal, cf.field_name, req.custom_value)
            deal.updated_at = now

        if prov:
            prov.source_value = cf.incoming_value
            prov.current_value = req.custom_value
            prov.is_overridden = True
            prov.last_update_source = "resolution"
            prov.updated_at = now

    else:
        raise HTTPException(status_code=400, detail=f"Invalid resolution choice '{choice}'. Must be keep_manual, accept_source, or custom_value.")

    cf.resolved_at = now

    log_audit_event(
        db,
        event_type="conflict_resolved",
        entity_type=cf.entity_type,
        entity_id=cf.entity_id,
        actor_label="Manager",
        before={"status": "pending", "current": cf.current_value, "incoming": cf.incoming_value},
        after={"choice": choice, "resolved_value": final_val},
        reason=f"Resolved via {choice}"
    )

    db.commit()
    return {"status": "resolved", "choice": choice, "final_value": final_val}

@router.get("/provenance/{entity_type}/{entity_id}", response_model=List[FieldProvenanceRead])
def get_entity_provenance(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    provs = db.query(FieldProvenance).filter(
        FieldProvenance.entity_type == entity_type,
        FieldProvenance.entity_id == entity_id
    ).all()
    return provs
