import os
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.clock import get_clock
from app.core.config import settings
from app.models.entities import ExportJob, ExportFile, ExportManifest
from app.schemas.schemas import ExportCreateRequest, ExportJobRead, ExportVerifyResponse
from app.services.export_service import generate_export_bundle, verify_export_integrity
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/exports", tags=["Export Center"])

@router.get("", response_model=List[ExportJobRead])
def list_export_jobs(db: Session = Depends(get_db)):
    jobs = db.query(ExportJob).order_by(ExportJob.id.desc()).all()
    results = []
    for j in jobs:
        m_dict = j.manifest.manifest_json if j.manifest else None
        files_read = []
        tot_records = 0
        for f in j.files:
            files_read.append({
                "file_name": f.file_name,
                "entity": f.entity,
                "record_count": f.record_count,
                "sha256": f.sha256,
                "size_bytes": f.size_bytes
            })
            tot_records += f.record_count

        if m_dict and "total_records" in m_dict:
            tot_records = m_dict["total_records"]

        results.append({
            "id": j.id,
            "format": j.format,
            "entities": j.entities,
            "filters": j.filters,
            "status": j.status,
            "validation_status": j.validation_status,
            "total_records": tot_records,
            "bundle_url": f"/api/exports/{j.id}/download",
            "created_at": j.created_at,
            "manifest": m_dict,
            "files": files_read
        })
    return results

@router.post("/generate", response_model=ExportJobRead)
def create_export(req: ExportCreateRequest, db: Session = Depends(get_db)):
    clock = get_clock()
    now = clock.now()

    job = ExportJob(
        format=req.format,
        entities=req.entities,
        filters=req.filters,
        status="completed",
        validation_status="verified",
        created_at=now
    )
    db.add(job)
    db.flush()

    manifest_data = generate_export_bundle(db, job, as_of=now)

    log_audit_event(
        db,
        event_type="export_generated",
        entity_type="export_job",
        entity_id=job.id,
        actor_label="User",
        after={"format": req.format, "entities": req.entities, "manifest_sha256": manifest_data.get("manifest_sha256")},
        reason="Export bundle created from Export Center"
    )

    db.commit()
    db.refresh(job)

    files_read = []
    tot_records = 0
    for f in job.files:
        files_read.append({
            "file_name": f.file_name,
            "entity": f.entity,
            "record_count": f.record_count,
            "sha256": f.sha256,
            "size_bytes": f.size_bytes
        })
        tot_records += f.record_count

    return {
        "id": job.id,
        "format": job.format,
        "entities": job.entities,
        "filters": job.filters,
        "status": job.status,
        "validation_status": job.validation_status,
        "total_records": tot_records,
        "bundle_url": f"/api/exports/{job.id}/download",
        "created_at": job.created_at,
        "manifest": manifest_data,
        "files": files_read
    }

@router.get("/{id}/manifest")
def get_export_manifest(id: int, db: Session = Depends(get_db)):
    job = db.query(ExportJob).filter(ExportJob.id == id).first()
    if not job or not job.manifest:
        raise HTTPException(status_code=404, detail="Export manifest not found")
    return job.manifest.manifest_json

@router.get("/{id}/download")
def download_export_file(
    id: int,
    file_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    job = db.query(ExportJob).filter(ExportJob.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    target_dir = os.path.join(settings.EXPORTS_DIR, f"export_{id}")

    if file_name:
        fpath = os.path.join(target_dir, file_name)
        if not os.path.exists(fpath):
            raise HTTPException(status_code=404, detail=f"File {file_name} not found")
        return FileResponse(fpath, filename=file_name)
    else:
        # Default return zip bundle
        zip_path = os.path.join(target_dir, f"export_bundle_{id}.zip")
        if not os.path.exists(zip_path):
            raise HTTPException(status_code=404, detail="Zip bundle not found")
        return FileResponse(zip_path, filename=f"revpilot_export_{id}.zip")

@router.post("/{id}/verify", response_model=ExportVerifyResponse)
def verify_export(id: int, db: Session = Depends(get_db)):
    """
    Cryptographic verification endpoint.
    Re-hashes files on disk, verifies against stored manifest hashes, and reports match/mismatch.
    """
    res = verify_export_integrity(db, id)
    return res
