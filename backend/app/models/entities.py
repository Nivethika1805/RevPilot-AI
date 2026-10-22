from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Text, DateTime, ForeignKey, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="rep")  # admin, manager, rep, demo_evaluator
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    team = relationship("Team", back_populates="members")
    deals = relationship("Deal", back_populates="owner")
    actions = relationship("FollowUpAction", back_populates="owner")

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    responsibilities = Column(JSON, nullable=True)  # list of strings: ["pricing", "renewals", "technical"]
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    members = relationship("User", back_populates="team")

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), index=True, nullable=False)
    industry = Column(String(255), nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    synthetic_flag = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    owner = relationship("User")
    deals = relationship("Deal", back_populates="account")

class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, nullable=True, index=True)
    deal_code = Column(String(50), unique=True, index=True, nullable=False)  # e.g., "DL-1001"
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    value = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), default="USD", nullable=False)
    stage = Column(String(50), nullable=False, default="Discovery")  # Discovery, Proposal, Negotiation, Legal/Review, Closed
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), default="open", nullable=False, index=True)  # open, won, lost
    expected_close_date = Column(DateTime, nullable=True, index=True)
    renewal_date = Column(DateTime, nullable=True, index=True)
    last_activity_at = Column(DateTime, nullable=True, index=True)
    next_activity_at = Column(DateTime, nullable=True, index=True)
    source_tracks_next_steps = Column(Boolean, default=True, nullable=False)
    decision_maker_known = Column(Boolean, nullable=True)  # tri-state: None=unknown, True=known, False=missing
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    account = relationship("Account", back_populates="deals")
    owner = relationship("User", back_populates="deals")
    conversations = relationship("Conversation", back_populates="deal")
    activities = relationship("Activity", back_populates="deal")
    risk_assessments = relationship("RiskAssessment", back_populates="deal", order_by="desc(RiskAssessment.id)")
    alerts = relationship("Alert", back_populates="deal")
    actions = relationship("FollowUpAction", back_populates="deal")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String(50), nullable=False, default="call")  # call, meeting, email, note
    occurred_at = Column(DateTime, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    customer_intent = Column(String(255), nullable=True)
    sentiment_label = Column(String(50), nullable=True)  # positive, neutral, negative, not_enough_evidence
    sentiment_basis = Column(Text, nullable=True)
    urgency = Column(String(50), default="medium", nullable=False)  # low, medium, high, critical
    priority = Column(String(50), default="medium", nullable=False)
    raw_text = Column(Text, nullable=False)
    source_file = Column(String(255), nullable=True)
    source_record_ref = Column(String(255), nullable=False, index=True)  # e.g., "CALL-2043"
    recommended_next_action = Column(String(255), nullable=True)
    routing_status = Column(String(50), default="recommended", nullable=False)  # recommended, accepted, overridden, unassigned_review
    content_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    deal = relationship("Deal", back_populates="conversations")
    account = relationship("Account")
    assigned_user = relationship("User")
    evidence_excerpts = relationship("EvidenceExcerpt", back_populates="conversation", cascade="all, delete-orphan")
    findings = relationship("ConversationFinding", back_populates="conversation", cascade="all, delete-orphan")
    routing_decisions = relationship("RoutingDecision", back_populates="conversation", order_by="desc(RoutingDecision.id)")

class EvidenceExcerpt(Base):
    __tablename__ = "evidence_excerpts"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # call_transcript, meeting_note, email_body, activity_note
    source_ref = Column(String(255), nullable=False, index=True)  # e.g. "CALL-2043#L12-L15"
    excerpt_text = Column(Text, nullable=False)
    start_offset = Column(Integer, nullable=True)
    end_offset = Column(Integer, nullable=True)
    occurred_at = Column(DateTime, nullable=False)
    extractor = Column(String(50), default="rules", nullable=False)  # rules, llm, manual
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="evidence_excerpts")
    findings = relationship("ConversationFinding", back_populates="evidence")

class ConversationFinding(Base):
    __tablename__ = "conversation_findings"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(50), nullable=False, index=True)  # objection, unresolved_question, competitor_mention, follow_up_commitment, intent, sentiment_indicator
    label = Column(String(255), nullable=False)
    status = Column(String(50), default="open", nullable=False, index=True)  # open, resolved
    evidence_id = Column(Integer, ForeignKey("evidence_excerpts.id", ondelete="CASCADE"), nullable=True)
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="findings")
    evidence = relationship("EvidenceExcerpt", back_populates="findings")

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String(50), nullable=False, index=True)  # email_sent, customer_reply, meeting_scheduled, meeting_postponed, meeting_held, proposal_sent
    occurred_at = Column(DateTime, nullable=False, index=True)
    detail = Column(Text, nullable=False)
    source_ref = Column(String(255), nullable=False, index=True)  # e.g., "ACT-5521"
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    deal = relationship("Deal", back_populates="activities")
    user = relationship("User")

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    assessed_at = Column(DateTime, default=utc_now, nullable=False)
    as_of = Column(DateTime, nullable=False)
    rules_version = Column(Integer, default=1, nullable=False)
    config_snapshot = Column(JSON, nullable=False)
    score = Column(Float, nullable=False)  # 0 - 100
    category = Column(String(50), nullable=False)  # Low, Medium, High, Critical
    data_completeness_pct = Column(Float, nullable=False)  # 0 - 100
    confidence_note = Column(String(255), nullable=True)
    trigger = Column(String(50), default="scheduled", nullable=False)  # scheduled, import, manual, simulation_commit
    previous_assessment_id = Column(Integer, ForeignKey("risk_assessments.id", ondelete="SET NULL"), nullable=True)
    is_current = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    deal = relationship("Deal", back_populates="risk_assessments")
    signals = relationship("RiskSignal", back_populates="assessment", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="assessment")

class RiskSignal(Base):
    __tablename__ = "risk_signals"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("risk_assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    signal_code = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False)  # detected, not_detected, unknown
    severity = Column(String(50), nullable=False)  # low, medium, high, critical
    weight_applied = Column(Float, default=0.0, nullable=False)
    score_contribution = Column(Float, default=0.0, nullable=False)
    explanation = Column(Text, nullable=False)
    why_it_matters = Column(Text, nullable=False)
    evidence_ids = Column(JSON, nullable=True)  # List of {source_ref, excerpt_text, occurred_at, type}
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    assessment = relationship("RiskAssessment", back_populates="signals")

class RiskConfig(Base):
    __tablename__ = "risk_config"

    id = Column(Integer, primary_key=True, index=True)
    signal_code = Column(String(100), unique=True, nullable=False)
    weight = Column(Float, nullable=False)
    threshold_params = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = Column(Integer, ForeignKey("risk_assessments.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="open", nullable=False, index=True)  # open, acknowledged, in_progress, resolved, reopened
    resolution_note = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    reopened_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    deal = relationship("Deal", back_populates="alerts")
    assessment = relationship("RiskAssessment", back_populates="alerts")
    resolver = relationship("User")

class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    priority_order = Column(Integer, nullable=False, index=True)  # Lower is higher precedence
    conditions = Column(JSON, nullable=False)  # e.g., {"topic": "pricing", "urgency": "high"}
    target_owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    priority_outcome = Column(String(50), default="medium", nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    specificity = Column(Integer, default=1, nullable=False)  # Number of matched clauses
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    target_owner = relationship("User")
    target_team = relationship("Team")

class RoutingDecision(Base):
    __tablename__ = "routing_decisions"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    decided_at = Column(DateTime, default=utc_now, nullable=False)
    rules_evaluated = Column(JSON, nullable=False)  # List of all evaluated rules and match boolean
    matched_rule_ids = Column(JSON, nullable=False)
    winning_rule_id = Column(Integer, ForeignKey("routing_rules.id", ondelete="SET NULL"), nullable=True)
    recommended_owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    alternative_owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    priority = Column(String(50), default="medium", nullable=False)
    reason = Column(Text, nullable=False)
    evidence_ids = Column(JSON, nullable=True)
    status = Column(String(50), default="recommended", nullable=False)  # recommended, accepted, overridden, unassigned_review
    override_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    override_owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    override_reason = Column(Text, nullable=True)
    is_current = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="routing_decisions")
    winning_rule = relationship("RoutingRule")
    recommended_owner = relationship("User", foreign_keys=[recommended_owner_id])
    alternative_owner = relationship("User", foreign_keys=[alternative_owner_id])
    override_owner = relationship("User", foreign_keys=[override_owner_id])

class FollowUpAction(Base):
    __tablename__ = "follow_up_actions"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    source = Column(String(50), default="recommended", nullable=False)  # recommended, manual
    title = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    evidence_ids = Column(JSON, nullable=True)
    priority = Column(String(50), default="medium", nullable=False, index=True)  # low, medium, high, critical
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    due_date = Column(DateTime, nullable=True, index=True)
    status = Column(String(50), default="open", nullable=False, index=True)  # open, in_progress, completed, snoozed, dismissed, superseded
    snoozed_until = Column(DateTime, nullable=True)
    dismissed_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    dedupe_key = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    deal = relationship("Deal", back_populates="actions")
    conversation = relationship("Conversation")
    owner = relationship("User", back_populates="actions")
    action_notes = relationship("ActionNote", back_populates="action", cascade="all, delete-orphan")

class ActionNote(Base):
    __tablename__ = "action_notes"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(Integer, ForeignKey("follow_up_actions.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    action = relationship("FollowUpAction", back_populates="action_notes")
    author = relationship("User")

class FieldProvenance(Base):
    __tablename__ = "field_provenance"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "field_name", name="uq_entity_field_provenance"),
    )

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # deal, account, conversation
    entity_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    source_value = Column(Text, nullable=True)
    current_value = Column(Text, nullable=True)
    previous_source_value = Column(Text, nullable=True)
    is_overridden = Column(Boolean, default=False, nullable=False)
    last_update_source = Column(String(50), default="import", nullable=False)  # import, manual, resolution, seed
    last_import_job_id = Column(Integer, ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

class FieldConflict(Base):
    __tablename__ = "field_conflicts"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    current_value = Column(Text, nullable=True)
    incoming_value = Column(Text, nullable=True)
    source_baseline_value = Column(Text, nullable=True)
    import_job_id = Column(Integer, ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, kept_manual, accepted_source, custom_value
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    resolver = relationship("User")

class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_sha256 = Column(String(64), nullable=False, index=True)
    format = Column(String(10), nullable=False)  # csv, json
    size_bytes = Column(Integer, nullable=False)
    status = Column(String(50), default="uploaded", nullable=False, index=True)  # uploaded, previewed, confirmed, completed, failed, rolled_back
    column_mapping = Column(JSON, nullable=True)
    summary = Column(JSON, nullable=True)  # {new: X, changed: Y, unchanged: Z, conflict: C, invalid: I, skipped: S}
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    row_results = relationship("ImportRowResult", back_populates="job", cascade="all, delete-orphan")

class ImportRowResult(Base):
    __tablename__ = "import_row_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    external_key = Column(String(255), nullable=True)
    match_method = Column(String(50), nullable=False)  # external_id, natural_key, none
    outcome = Column(String(50), nullable=False)  # new, changed, unchanged, conflict, invalid, skipped, duplicate_in_file
    errors = Column(JSON, nullable=True)
    changes = Column(JSON, nullable=True)
    row_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    job = relationship("ImportJob", back_populates="row_results")

class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    format = Column(String(10), nullable=False)  # csv, json, zip
    entities = Column(JSON, nullable=False)
    filters = Column(JSON, nullable=True)
    status = Column(String(50), default="completed", nullable=False)
    validation_status = Column(String(50), default="verified", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    manifest = relationship("ExportManifest", back_populates="export_job", uselist=False, cascade="all, delete-orphan")
    files = relationship("ExportFile", back_populates="export_job", cascade="all, delete-orphan")

class ExportManifest(Base):
    __tablename__ = "export_manifests"

    id = Column(Integer, primary_key=True, index=True)
    export_job_id = Column(Integer, ForeignKey("export_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    manifest_json = Column(JSON, nullable=False)
    manifest_sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    export_job = relationship("ExportJob", back_populates="manifest")

class ExportFile(Base):
    __tablename__ = "export_files"

    id = Column(Integer, primary_key=True, index=True)
    export_job_id = Column(Integer, ForeignKey("export_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    entity = Column(String(100), nullable=False)
    record_count = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    export_job = relationship("ExportJob", back_populates="files")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    occurred_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_label = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    import_job_id = Column(Integer, ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True)
    correlation_id = Column(String(64), nullable=False, index=True)

class FindingsReport(Base):
    __tablename__ = "findings_reports"

    id = Column(Integer, primary_key=True, index=True)
    generated_at = Column(DateTime, default=utc_now, nullable=False)
    as_of = Column(DateTime, nullable=False)
    items = Column(JSON, nullable=False)  # [{id, title, severity, description, deal_id, evidence_refs}]
    created_at = Column(DateTime, default=utc_now, nullable=False)
