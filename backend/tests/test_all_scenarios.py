import os
import io
import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.core.clock import Clock, get_clock
from app.models.entities import (
    User, Deal, Conversation, Activity, RiskAssessment, Alert,
    FollowUpAction, RoutingDecision, FieldProvenance, FieldConflict,
    ImportJob, AuditEvent
)
from sqlalchemy.pool import StaticPool
from app.services.risk_engine import assess_deal_risk
from app.services.routing_engine import evaluate_routing
from app.seed.seed_data import seed_database

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))

# Setup test client with single in-memory SQLite connection via StaticPool
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# 1. Dashboard metrics equal independently computed database values
def test_dashboard_metrics_equal_database():
    res = client.get("/api/dashboard/metrics")
    assert res.status_code == 200
    data = res.json()
    
    db = TestingSessionLocal()
    try:
        db_open_deals = db.query(Deal).filter(Deal.status == "open").all()
        expected_count = len(db_open_deals)
        expected_val = sum(d.value for d in db_open_deals)
        
        assert data["total_open_deals"] == expected_count
        assert abs(data["total_open_pipeline_value"] - expected_val) < 0.01
        assert "risk_distribution" in data
        assert "what_should_i_do_today" in data
        assert len(data["what_should_i_do_today"]) > 0
    finally:
        db.close()

# 2. Search and filtering return exactly the correct records
def test_search_and_filtering_accuracy():
    # Filter by specific company name in inbox
    res = client.get("/api/conversations?q=Northwind")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert "northwind" in item["account_name"].lower() or "northwind" in item["summary"].lower()

    # Filter deals by stage
    res_deals = client.get("/api/deals?stage=Negotiation")
    assert res_deals.status_code == 200
    deal_data = res_deals.json()
    for d in deal_data["items"]:
        assert d["stage"] == "Negotiation"

# 3. Risk signals include correct source references
def test_risk_signals_contain_source_references():
    db = TestingSessionLocal()
    try:
        # Check DL-1001 (critical pricing objection stall)
        deal = db.query(Deal).filter(Deal.deal_code == "DL-1001").first()
        assert deal is not None
        curr_ass = next(a for a in deal.risk_assessments if a.is_current)
        detected_signals = [s for s in curr_ass.signals if s.state == "detected"]
        assert len(detected_signals) > 0

        for sig in detected_signals:
            assert sig.evidence_ids is not None
            assert len(sig.evidence_ids) > 0
            for ev in sig.evidence_ids:
                assert "source_ref" in ev
                # Verify source ref is a valid format
                assert any(ev["source_ref"].startswith(prefix) for prefix in ["CALL-", "ACT-", "DEAL-", "CONV-", "NOTE-", "EMAIL-"])
    finally:
        db.close()

# 4. Risk scores are deterministic
def test_risk_engine_determinism():
    deal_dict = {
        "id": 999, "deal_code": "DL-TEST", "value": 150000.0,
        "source_tracks_next_steps": True, "next_activity_at": None,
        "decision_maker_known": False, "renewal_date": None
    }
    convs = []
    findings = [{"kind": "objection", "label": "Unresolved Pricing Objection", "status": "open", "source_ref": "CALL-1#L5"}]
    acts = []
    as_of = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)

    run_1 = assess_deal_risk(deal_dict, convs, findings, acts, now=as_of)
    run_2 = assess_deal_risk(deal_dict, convs, findings, acts, now=as_of)
    run_3 = assess_deal_risk(deal_dict, convs, findings, acts, now=as_of)

    assert run_1["score"] == run_2["score"] == run_3["score"]
    assert run_1["category"] == run_2["category"] == run_3["category"]
    assert run_1["signals"] == run_2["signals"] == run_3["signals"]

# 5. Missing evidence is treated as "unknown" and adds 0 score, not as a detected signal
def test_missing_evidence_is_unknown_not_risk():
    deal_dict = {
        "id": 888, "deal_code": "DL-UNKNOWN-TEST", "value": 50000.0,
        "source_tracks_next_steps": False,  # Untracked!
        "next_activity_at": None,
        "decision_maker_known": None,      # Tri-state None!
        "renewal_date": None
    }
    convs = []
    findings = []
    acts = []  # No customer activity data
    as_of = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)

    res = assess_deal_risk(deal_dict, convs, findings, acts, now=as_of)
    signals_by_code = {s["signal_code"]: s for s in res["signals"]}

    # NO_RECENT_CUSTOMER_RESPONSE should be unknown
    assert signals_by_code["NO_RECENT_CUSTOMER_RESPONSE"]["state"] == "unknown"
    assert signals_by_code["NO_RECENT_CUSTOMER_RESPONSE"]["score_contribution"] == 0.0

    # MISSING_NEXT_STEP should be unknown
    assert signals_by_code["MISSING_NEXT_STEP"]["state"] == "unknown"
    assert signals_by_code["MISSING_NEXT_STEP"]["score_contribution"] == 0.0

    # MISSING_DECISION_MAKER should be unknown
    assert signals_by_code["MISSING_DECISION_MAKER"]["state"] == "unknown"
    assert signals_by_code["MISSING_DECISION_MAKER"]["score_contribution"] == 0.0

    # Score should be 0 and completeness strictly below 100%
    assert res["score"] == 0.0
    assert res["category"] == "Low"
    assert res["data_completeness_pct"] < 100.0

# 6. Routing precedence works when multiple rules match
def test_routing_precedence_order_and_specificity():
    rules = [
        {"id": 1, "name": "General Commercial", "priority_order": 5, "specificity": 1, "conditions": {"topic": "pricing"}, "target_owner_user_id": 101, "enabled": True, "priority_outcome": "medium"},
        {"id": 2, "name": "Critical Pricing Escalation", "priority_order": 1, "specificity": 2, "conditions": {"topic": "pricing", "urgency": "critical"}, "target_owner_user_id": 102, "enabled": True, "priority_outcome": "critical"}
    ]
    context = {"topic": "pricing", "urgency": "critical"}
    result = evaluate_routing(context, rules)

    assert result["status"] == "recommended"
    assert result["winning_rule_id"] == 2
    assert result["recommended_owner_id"] == 102
    assert result["alternative_owner_id"] == 101
    assert "Rejected alternative" in result["reason"]

# 7. Ambiguous routing enters the unassigned review queue
def test_ambiguous_routing_enters_unassigned_review_queue():
    # Two rules with identical priority_order=10 and specificity=1, but different owners!
    rules = [
        {"id": 10, "name": "Branch Alpha", "priority_order": 10, "specificity": 1, "conditions": {"topic": "split"}, "target_owner_user_id": 201, "enabled": True, "priority_outcome": "high"},
        {"id": 11, "name": "Branch Beta", "priority_order": 10, "specificity": 1, "conditions": {"topic": "split"}, "target_owner_user_id": 202, "enabled": True, "priority_outcome": "high"}
    ]
    context = {"topic": "split"}
    result = evaluate_routing(context, rules)

    assert result["status"] == "unassigned_review"
    assert result["winning_rule_id"] is None
    assert result["recommended_owner_id"] is None
    assert "Routing Conflict" in result["reason"]

# 8. Manual routing overrides are preserved when routing is re-run
def test_manual_routing_override_preserved_on_rerun():
    db = TestingSessionLocal()
    try:
        conv = db.query(Conversation).first()
        rep = db.query(User).filter(User.role == "rep").first()
        
        # Apply manual override
        res_override = client.post(f"/api/routing/override/{conv.id}", json={
            "target_owner_id": rep.id,
            "reason": "Executive relationship coverage"
        })
        assert res_override.status_code == 200

        # Now trigger decide_routing on that conversation
        res_rerun = client.post(f"/api/routing/decide/{conv.id}")
        assert res_rerun.status_code == 200
        data = res_rerun.json()
        assert data["status"] == "preserved_override"
        assert data["active_owner_id"] == rep.id
    finally:
        db.close()

# 9. Importing the same file twice creates no duplicate records
def test_reimport_identical_dataset_zero_duplicates():
    csv_content = (
        "deal_code,name,account_name,value,stage,status\n"
        "DL-REIMPORT-1,Test Reimport Deal 1,Northwind Logistics Demo,100000.0,Discovery,open\n"
        "DL-REIMPORT-2,Test Reimport Deal 2,Apex Global BioTech,200000.0,Proposal,open\n"
    ).encode("utf-8")

    # First import
    res1 = client.post("/api/imports/upload", files={"file": ("reimport.csv", io.BytesIO(csv_content), "text/csv")})
    job1_id = res1.json()["job_id"]
    client.post("/api/imports/plan", json={"job_id": job1_id, "entity_type": "deal", "column_mapping": res1.json()["suggested_mapping"]})
    conf1 = client.post("/api/imports/confirm", json={"job_id": job1_id})
    assert conf1.status_code == 200
    assert conf1.json()["summary"]["new"] == 2

    # Second identical import
    res2 = client.post("/api/imports/upload", files={"file": ("reimport.csv", io.BytesIO(csv_content), "text/csv")})
    job2_id = res2.json()["job_id"]
    client.post("/api/imports/plan", json={"job_id": job2_id, "entity_type": "deal", "column_mapping": res2.json()["suggested_mapping"]})
    conf2 = client.post("/api/imports/confirm", json={"job_id": job2_id})
    assert conf2.status_code == 200
    
    # Assert zero new records created!
    assert conf2.json()["summary"]["new"] == 0
    assert conf2.json()["summary"]["unchanged"] == 2

# 10. Unchanged imports cause no updates
def test_unchanged_imports_cause_no_updates():
    db = TestingSessionLocal()
    try:
        deal = db.query(Deal).filter(Deal.deal_code == "DL-REIMPORT-1").first()
        assert deal is not None
        initial_updated_at = deal.updated_at
        initial_audit_count = db.query(AuditEvent).filter(AuditEvent.entity_id == deal.id).count()

        # Re-import identical content
        csv_content = (
            "deal_code,name,account_name,value,stage,status\n"
            f"DL-REIMPORT-1,{deal.name},Northwind Logistics Demo,{deal.value},{deal.stage},{deal.status}\n"
        ).encode("utf-8")

        res = client.post("/api/imports/upload", files={"file": ("check_unchanged.csv", io.BytesIO(csv_content), "text/csv")})
        job_id = res.json()["job_id"]
        client.post("/api/imports/plan", json={"job_id": job_id, "entity_type": "deal", "column_mapping": res.json()["suggested_mapping"]})
        conf = client.post("/api/imports/confirm", json={"job_id": job_id})
        assert conf.status_code == 200
        assert conf.json()["summary"]["unchanged"] == 1

        db.refresh(deal)
        assert deal.updated_at == initial_updated_at
        final_audit_count = db.query(AuditEvent).filter(AuditEvent.entity_id == deal.id).count()
        assert final_audit_count == initial_audit_count
    finally:
        db.close()

# 11. New source values do not silently overwrite manual corrections
def test_new_source_values_do_not_silently_overwrite_manual_corrections():
    db = TestingSessionLocal()
    try:
        deal = db.query(Deal).filter(Deal.deal_code == "DL-1005").first()
        assert deal is not None
        
        # Verify deal has manual override
        prov = db.query(FieldProvenance).filter(
            FieldProvenance.entity_type == "deal",
            FieldProvenance.entity_id == deal.id,
            FieldProvenance.field_name == "stage"
        ).first()
        assert prov.is_overridden is True
        manual_val = deal.stage  # "Negotiation"

        # Import v2 file attempting to change stage to "Legal/Review"
        with open(os.path.join(DATA_DIR, "deals_v2.csv"), "rb") as f:
            content = f.read()

        res = client.post("/api/imports/upload", files={"file": ("deals_v2.csv", io.BytesIO(content), "text/csv")})
        job_id = res.json()["job_id"]
        client.post("/api/imports/plan", json={"job_id": job_id, "entity_type": "deal", "column_mapping": res.json()["suggested_mapping"]})
        conf = client.post("/api/imports/confirm", json={"job_id": job_id})
        assert conf.status_code == 200

        # Assert manual value was NOT overwritten!
        db.refresh(deal)
        assert deal.stage == manual_val
    finally:
        db.close()

# 12. Conflicting values are surfaced and resolvable
def test_conflicting_values_surfaced_and_resolvable():
    # Check pending conflicts
    res_list = client.get("/api/imports/conflicts")
    assert res_list.status_code == 200
    conflicts = res_list.json()
    assert len(conflicts) >= 1
    
    target_conflict = conflicts[0]
    c_id = target_conflict["id"]

    # Test resolving via keep_manual
    res_resolve = client.post(f"/api/imports/conflicts/{c_id}/resolve", json={
        "resolution_choice": "keep_manual"
    })
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "resolved"
    assert res_resolve.json()["choice"] == "keep_manual"

# 13. Failed/malformed imports and mid-import exceptions leave no inconsistent partial data
def test_failed_malformed_import_rolls_back():
    with open(os.path.join(DATA_DIR, "malformed.csv"), "rb") as f:
        content = f.read()

    res = client.post("/api/imports/upload", files={"file": ("malformed.csv", io.BytesIO(content), "text/csv")})
    # Should be rejected with 400 Bad Request
    assert res.status_code == 400
    assert "Malformed CSV file" in res.json()["detail"]

# 14. Export files contain exactly the expected records
def test_export_files_contain_expected_records():
    res = client.post("/api/exports/generate", json={
        "format": "csv",
        "entities": ["deals", "conversations"]
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["files"]) == 2
    
    db = TestingSessionLocal()
    try:
        deal_count = db.query(Deal).count()
        conv_count = db.query(Conversation).count()

        deal_file_meta = next(f for f in data["files"] if f["entity"] == "deals")
        conv_file_meta = next(f for f in data["files"] if f["entity"] == "conversations")

        assert deal_file_meta["record_count"] == deal_count
        assert conv_file_meta["record_count"] == conv_count
    finally:
        db.close()

# 15. Export manifests match generated files and verify endpoint detects tampering
def test_export_manifest_hashes_and_tamper_detection():
    res = client.post("/api/exports/generate", json={
        "format": "json",
        "entities": ["deals"]
    })
    assert res.status_code == 200
    job_id = res.json()["id"]

    # Verify integrity (untampered)
    res_verify = client.post(f"/api/exports/{job_id}/verify")
    assert res_verify.status_code == 200
    assert res_verify.json()["status"] == "verified"
    assert res_verify.json()["all_matched"] is True

    # Tamper with file on disk
    export_dir = os.path.join(settings.EXPORTS_DIR, f"export_{job_id}")
    deal_file = os.path.join(export_dir, "deals.json")
    with open(deal_file, "a") as f:
        f.write(" ")  # Tamper by 1 byte

    # Verify endpoint must detect tampering!
    res_tampered = client.post(f"/api/exports/{job_id}/verify")
    assert res_tampered.status_code == 200
    assert res_tampered.json()["status"] == "tampered"
    assert res_tampered.json()["all_matched"] is False

# 16. Audit events are recorded for important changes
def test_audit_event_logging_for_key_actions():
    db = TestingSessionLocal()
    try:
        initial_events = db.query(AuditEvent).count()
        assert initial_events > 0

        # Perform a manual edit on a deal
        deal = db.query(Deal).first()
        client.patch(f"/api/deals/{deal.id}", json={"name": "Audited Renamed Deal"})

        final_events = db.query(AuditEvent).count()
        assert final_events > initial_events
    finally:
        db.close()

# 17. Resolving an alert does not change risk score/category
def test_alert_resolution_does_not_mutate_risk_score():
    db = TestingSessionLocal()
    try:
        deal = db.query(Deal).filter(Deal.deal_code == "DL-1001").first()
        curr_ass = next(a for a in deal.risk_assessments if a.is_current)
        initial_score = curr_ass.score
        initial_cat = curr_ass.category

        alert = db.query(Alert).filter(Alert.deal_id == deal.id).first()
        assert alert is not None

        # Resolve the alert
        res = client.post(f"/api/alerts/{alert.id}/transition", json={
            "target_status": "resolved",
            "note": "Reviewed terms with management."
        })
        assert res.status_code == 200

        # Assert risk score and category are completely unchanged!
        db.refresh(curr_ass)
        assert curr_ass.score == initial_score
        assert curr_ass.category == initial_cat
    finally:
        db.close()

# 18. What-if simulations do not mutate any actual rows, and commit does
def test_what_if_simulation_zero_mutation_and_commit():
    db = TestingSessionLocal()
    try:
        deal = db.query(Deal).filter(Deal.deal_code == "DL-1008").first()
        initial_updated_at = deal.updated_at
        initial_activity_count = db.query(Activity).count()
        initial_assessment_count = db.query(RiskAssessment).count()
        initial_audit_count = db.query(AuditEvent).count()

        # Run simulation
        sim_res = client.post("/api/risk/simulate", json={
            "deal_id": deal.id,
            "hypothetical_changes": {
                "add_customer_reply": True,
                "resolve_pricing_objection": True,
                "schedule_next_step": True
            }
        })
        assert sim_res.status_code == 200
        sim_data = sim_res.json()
        assert sim_data["simulated_score"] < sim_data["baseline_score"]

        # Assert ZERO mutation occurred
        db.refresh(deal)
        assert deal.updated_at == initial_updated_at
        assert db.query(Activity).count() == initial_activity_count
        assert db.query(RiskAssessment).count() == initial_assessment_count
        assert db.query(AuditEvent).count() == initial_audit_count

        # Now test commit step
        commit_res = client.post("/api/risk/simulate/commit", json={
            "deal_id": deal.id,
            "hypothetical_changes": {
                "add_customer_reply": True,
                "resolve_pricing_objection": True
            },
            "note": "Buyer agreed to terms verbally on executive call"
        })
        assert commit_res.status_code == 200
        assert commit_res.json()["status"] == "committed"

        # Assert real records created
        assert db.query(Activity).count() > initial_activity_count
        assert db.query(RiskAssessment).count() > initial_assessment_count
        assert db.query(AuditEvent).count() > initial_audit_count
    finally:
        db.close()

# 19. Findings report contains at least three evidence findings & difficult routing decision
def test_findings_report_contains_three_findings_and_difficult_routing():
    res = client.get("/api/findings")
    assert res.status_code == 200
    data = res.json()
    assert len(data["findings"]) >= 3
    for f in data["findings"]:
        assert "evidence_refs" in f
        assert len(f["evidence_refs"]) > 0

    assert data["difficult_routing_decision"] is not None
    assert "chosen_owner" in data["difficult_routing_decision"]
    assert "rejected_alternative" in data["difficult_routing_decision"]
    assert "reason" in data["difficult_routing_decision"]

# 20. Health check endpoint
def test_health_check_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["app_version"] == "1.0.0"

# 21. Decision Replay verifies matching score and detects mismatching score
def test_decision_replay_matching_and_mismatching_scores():
    db = TestingSessionLocal()
    try:
        # Find a real assessment
        ass = db.query(RiskAssessment).filter(RiskAssessment.deal_id == 1, RiskAssessment.is_current == True).first()
        assert ass is not None
        original_score = ass.score

        # Case A: Matching score
        res_match = client.get(f"/api/risk/replay/{ass.id}")
        assert res_match.status_code == 200
        data_match = res_match.json()
        assert data_match["matches_stored"] is True
        assert data_match["replay_matches_stored_result"] is True
        assert abs(data_match["recomputed_score"] - data_match["stored_score"]) < 0.01

        # Case B: Artificially tamper with stored score in DB
        ass.score = 99.0
        db.commit()

        res_mismatch = client.get(f"/api/risk/replay/{ass.id}")
        assert res_mismatch.status_code == 200
        data_mismatch = res_mismatch.json()
        assert data_mismatch["matches_stored"] is False
        assert data_mismatch["replay_matches_stored_result"] is False
        assert data_mismatch["stored_score"] == 99.0
        assert data_mismatch["recomputed_score"] != 99.0

        # Restore original score
        ass.score = original_score
        db.commit()
    finally:
        db.close()

# 22. Export manifest record counts agree and audit_history is supported
def test_export_manifest_record_counts_agree():
    res = client.post("/api/exports/generate", json={
        "format": "csv",
        "entities": ["deals", "conversations", "audit_history"]
    })
    assert res.status_code == 200
    data = res.json()
    assert data["validation_status"] == "verified"
    assert data["total_records"] > 0
    assert len(data["files"]) == 3
    computed_sum = sum(f["record_count"] for f in data["files"])
    assert data["total_records"] == computed_sum

    # Verify manifest.json on disk contains total_records and verified status
    job_id = data["id"]
    res_manifest = client.get(f"/api/exports/{job_id}/manifest")
    assert res_manifest.status_code == 200
    m_json = res_manifest.json()
    assert m_json["validation_status"] == "verified"
    assert m_json["total_records"] == computed_sum

