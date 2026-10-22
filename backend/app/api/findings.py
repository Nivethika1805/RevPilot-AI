import io
import csv
import json
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.clock import get_clock
from app.schemas.schemas import FindingsReportResponse
from app.services.findings_service import generate_evidence_findings, format_findings_as_markdown
from app.services.export_service import sanitize_csv_cell

router = APIRouter(prefix="/findings", tags=["Findings & Evidence Report"])

@router.get("", response_model=FindingsReportResponse)
def get_findings_report(db: Session = Depends(get_db)):
    clock = get_clock()
    now = clock.now()
    report = generate_evidence_findings(db, as_of=now)
    return report

@router.get("/export")
def export_findings(
    format: str = Query("markdown", pattern="^(markdown|json|csv)$"),
    db: Session = Depends(get_db)
):
    clock = get_clock()
    now = clock.now()
    report = generate_evidence_findings(db, as_of=now)

    if format == "json":
        json_str = json.dumps(report, default=str, indent=2)
        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=findings_report.json"}
        )
    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "severity", "title", "deal_code", "deal_name", "description", "recommended_action", "evidence_refs"])
        for f in report.get("findings", []):
            ev_str = "; ".join(f"{e.get('source_ref')}: {e.get('detail', e.get('label', ''))}" for e in f.get("evidence_refs", []))
            writer.writerow([
                f["id"],
                f["severity"],
                f["title"],
                f.get("deal_code", ""),
                f.get("deal_name", ""),
                f["description"],
                f["recommended_action"],
                sanitize_csv_cell(ev_str)
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=findings_report.csv"}
        )
    else:
        # Default Markdown
        md_text = format_findings_as_markdown(report)
        return Response(
            content=md_text,
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=findings_report.md"}
        )
