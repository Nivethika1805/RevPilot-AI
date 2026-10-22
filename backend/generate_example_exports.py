import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.core.clock import get_clock
from app.models.entities import ExportJob
from app.services.export_service import generate_export_bundle

if __name__ == "__main__":
    db = SessionLocal()
    try:
        clock = get_clock()
        now = clock.now()

        # Generate CSV export
        job_csv = ExportJob(
            format="csv",
            entities=["deals", "conversations", "risk_assessments", "follow_up_actions"],
            status="completed",
            validation_status="verified",
            created_at=now
        )
        db.add(job_csv)
        db.flush()

        examples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "exports", "examples"))
        manifest_data = generate_export_bundle(db, job_csv, as_of=now, base_dir=examples_dir)
        db.commit()
        print("Generated example export in:", examples_dir)
        print("Manifest SHA256:", manifest_data.get("manifest_sha256"))
    finally:
        db.close()
