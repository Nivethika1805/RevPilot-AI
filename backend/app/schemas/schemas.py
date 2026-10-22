from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

# Base
class OrmModel(BaseModel):
    class Config:
        from_attributes = True

# Auth
class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class LoginRequest(BaseModel):
    email: str
    password: str

# User
class UserRead(OrmModel):
    id: int
    email: str
    name: str
    role: str
    team_id: Optional[int] = None
    is_active: bool
    created_at: datetime

# Team
class TeamRead(OrmModel):
    id: int
    name: str
    responsibilities: Optional[List[str]] = None
    created_at: datetime

# Account
class AccountRead(OrmModel):
    id: int
    external_id: Optional[str] = None
    name: str
    normalized_name: str
    industry: Optional[str] = None
    owner_user_id: Optional[int] = None
    synthetic_flag: bool = True
    created_at: datetime

# Activity
class ActivityRead(OrmModel):
    id: int
    external_id: Optional[str] = None
    deal_id: int
    user_id: Optional[int] = None
    type: str
    occurred_at: datetime
    detail: str
    source_ref: str
    created_at: datetime
    user_name: Optional[str] = None

# Evidence Excerpt
class EvidenceExcerptRead(OrmModel):
    id: int
    conversation_id: int
    source_type: str
    source_ref: str
    excerpt_text: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    occurred_at: datetime
    extractor: str
    created_at: datetime

# Finding
class ConversationFindingRead(OrmModel):
    id: int
    conversation_id: int
    kind: str
    label: str
    status: str
    evidence_id: Optional[int] = None
    confidence: Optional[float] = None
    evidence: Optional[EvidenceExcerptRead] = None
    created_at: datetime

# Conversation
class ConversationRead(OrmModel):
    id: int
    external_id: Optional[str] = None
    deal_id: int
    account_id: int
    assigned_user_id: Optional[int] = None
    type: str
    occurred_at: datetime
    summary: str
    customer_intent: Optional[str] = None
    sentiment_label: Optional[str] = None
    sentiment_basis: Optional[str] = None
    urgency: str
    priority: str
    source_file: Optional[str] = None
    source_record_ref: str
    recommended_next_action: Optional[str] = None
    routing_status: str
    created_at: datetime
    deal_name: Optional[str] = None
    account_name: Optional[str] = None
    assigned_user_name: Optional[str] = None

class ConversationDetail(ConversationRead):
    raw_text: str
    evidence_excerpts: List[EvidenceExcerptRead] = []
    findings: List[ConversationFindingRead] = []
    routing_decision: Optional[Dict[str, Any]] = None

class ConversationUpdate(BaseModel):
    assigned_user_id: Optional[int] = None
    priority: Optional[str] = None
    urgency: Optional[str] = None
    recommended_next_action: Optional[str] = None

# Risk Assessment & Signals
class RiskSignalRead(OrmModel):
    id: int
    assessment_id: int
    signal_code: str
    state: str
    severity: str
    weight_applied: float
    score_contribution: float
    explanation: str
    why_it_matters: str
    evidence_ids: Optional[List[Dict[str, Any]]] = None

class RiskAssessmentRead(OrmModel):
    id: int
    deal_id: int
    assessed_at: datetime
    as_of: datetime
    rules_version: int
    config_snapshot: Dict[str, Any]
    score: float
    category: str
    data_completeness_pct: float
    confidence_note: Optional[str] = None
    trigger: str
    previous_assessment_id: Optional[int] = None
    is_current: bool
    signals: List[RiskSignalRead] = []

class RiskConfigRead(OrmModel):
    id: int
    signal_code: str
    weight: float
    threshold_params: Dict[str, Any]
    enabled: bool
    version: int

class RiskConfigUpdate(BaseModel):
    weight: Optional[float] = None
    threshold_params: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None

# Alert
class AlertRead(OrmModel):
    id: int
    deal_id: int
    assessment_id: int
    status: str
    resolution_note: Optional[str] = None
    resolved_by: Optional[int] = None
    resolved_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    reopened_reason: Optional[str] = None
    created_at: datetime

class AlertTransitionRequest(BaseModel):
    target_status: str  # acknowledged, in_progress, resolved, reopened
    note: Optional[str] = None  # required if resolving or reopening

# Deals
class DealRead(OrmModel):
    id: int
    external_id: Optional[str] = None
    deal_code: str
    account_id: int
    account_name: Optional[str] = None
    name: str
    value: float
    currency: str
    stage: str
    owner_user_id: Optional[int] = None
    owner_name: Optional[str] = None
    status: str
    expected_close_date: Optional[datetime] = None
    renewal_date: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    next_activity_at: Optional[datetime] = None
    source_tracks_next_steps: bool
    decision_maker_known: Optional[bool] = None
    created_at: datetime
    updated_at: datetime
    # Current risk metrics
    current_risk_score: Optional[float] = None
    current_risk_category: Optional[str] = None
    data_completeness_pct: Optional[float] = None
    has_manual_override: bool = False
    open_alerts_count: int = 0
    open_actions_count: int = 0

class DealDetail(DealRead):
    current_assessment: Optional[RiskAssessmentRead] = None
    recent_conversations: List[ConversationRead] = []
    recent_activities: List[ActivityRead] = []
    actions: List[Any] = []
    alerts: List[AlertRead] = []
    field_provenances: List[Dict[str, Any]] = []

class DealUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = None
    stage: Optional[str] = None
    owner_user_id: Optional[int] = None
    expected_close_date: Optional[datetime] = None
    next_activity_at: Optional[datetime] = None
    decision_maker_known: Optional[bool] = None

# Actions
class ActionNoteRead(OrmModel):
    id: int
    action_id: int
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    body: str
    created_at: datetime

class ActionNoteCreate(BaseModel):
    body: str

class FollowUpActionRead(OrmModel):
    id: int
    deal_id: int
    deal_name: Optional[str] = None
    deal_code: Optional[str] = None
    account_name: Optional[str] = None
    conversation_id: Optional[int] = None
    source: str
    title: str
    reason: str
    evidence_ids: Optional[List[Dict[str, Any]]] = None
    priority: str
    owner_user_id: Optional[int] = None
    owner_name: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str
    snoozed_until: Optional[datetime] = None
    dismissed_reason: Optional[str] = None
    notes: Optional[str] = None
    dedupe_key: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    notes_list: List[ActionNoteRead] = []

class FollowUpActionCreate(BaseModel):
    deal_id: int
    conversation_id: Optional[int] = None
    title: str
    reason: str
    priority: str = "medium"
    owner_user_id: Optional[int] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None

class FollowUpActionUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = None
    owner_user_id: Optional[int] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    snoozed_until: Optional[datetime] = None
    dismissed_reason: Optional[str] = None
    notes: Optional[str] = None

# Routing Rules & Decisions
class RoutingRuleRead(OrmModel):
    id: int
    name: str
    priority_order: int
    conditions: Dict[str, Any]
    target_owner_user_id: Optional[int] = None
    target_owner_name: Optional[str] = None
    target_team_id: Optional[int] = None
    target_team_name: Optional[str] = None
    priority_outcome: str
    enabled: bool
    version: int
    specificity: int
    created_at: datetime

class RoutingRuleCreate(BaseModel):
    name: str
    priority_order: int
    conditions: Dict[str, Any]
    target_owner_user_id: Optional[int] = None
    target_team_id: Optional[int] = None
    priority_outcome: str = "medium"
    enabled: bool = True

class RoutingRuleUpdate(BaseModel):
    name: Optional[str] = None
    priority_order: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None
    target_owner_user_id: Optional[int] = None
    target_team_id: Optional[int] = None
    priority_outcome: Optional[str] = None
    enabled: Optional[bool] = None

class RoutingDecisionRead(OrmModel):
    id: int
    conversation_id: int
    decided_at: datetime
    rules_evaluated: List[Dict[str, Any]]
    matched_rule_ids: List[int]
    winning_rule_id: Optional[int] = None
    winning_rule_name: Optional[str] = None
    recommended_owner_id: Optional[int] = None
    recommended_owner_name: Optional[str] = None
    alternative_owner_id: Optional[int] = None
    alternative_owner_name: Optional[str] = None
    priority: str
    reason: str
    evidence_ids: Optional[List[Dict[str, Any]]] = None
    status: str
    override_by: Optional[int] = None
    override_owner_id: Optional[int] = None
    override_owner_name: Optional[str] = None
    override_reason: Optional[str] = None
    is_current: bool

class RoutingOverrideRequest(BaseModel):
    target_owner_id: int
    reason: str

class RoutingDryRunRequest(BaseModel):
    conditions: Dict[str, Any]

# Decision Replay & Simulation
class ReplayResponse(BaseModel):
    assessment_id: int
    stored_score: float
    recomputed_score: float
    matches_stored: bool
    replay_matches_stored_result: Optional[bool] = None
    stored_rules_version: int = 1
    stored_category: Optional[str] = None
    recomputed_category: Optional[str] = None
    input_records: Dict[str, Any]
    score_delta_vs_previous: Optional[float] = None
    signals_added: List[str] = []
    signals_removed: List[str] = []
    signals: List[Dict[str, Any]]


class SimulationRequest(BaseModel):
    deal_id: int
    hypothetical_changes: Dict[str, Any]  # e.g., {"add_activity": "customer_reply", "resolve_objections": ["pricing"], "set_next_step": true}

class SimulationResponse(BaseModel):
    deal_id: int
    deal_code: str
    deal_name: str
    as_of: datetime
    baseline_score: float
    baseline_category: str
    simulated_score: float
    simulated_category: str
    score_delta: float
    signals_resolved: List[str]
    signals_remaining: List[str]
    new_signals_detected: List[str]
    recommended_actions: List[str]
    disclaimer: str = "SIMULATION — not saved. A lower risk index does not mean the deal will close."

class CommitSimulationRequest(BaseModel):
    deal_id: int
    hypothetical_changes: Dict[str, Any]
    note: str

# Provenance & Conflict
class FieldProvenanceRead(OrmModel):
    id: int
    entity_type: str
    entity_id: int
    field_name: str
    source_value: Optional[str] = None
    current_value: Optional[str] = None
    previous_source_value: Optional[str] = None
    is_overridden: bool
    last_update_source: str
    last_import_job_id: Optional[int] = None
    updated_at: datetime

class FieldConflictRead(OrmModel):
    id: int
    entity_type: str
    entity_id: int
    entity_label: Optional[str] = None
    field_name: str
    current_value: Optional[str] = None
    incoming_value: Optional[str] = None
    source_baseline_value: Optional[str] = None
    import_job_id: int
    status: str
    resolved_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolution_value: Optional[str] = None
    created_at: datetime

class ConflictResolveRequest(BaseModel):
    resolution_choice: str  # keep_manual, accept_source, custom_value
    custom_value: Optional[str] = None

# Imports
class ImportUploadResponse(BaseModel):
    job_id: int
    filename: str
    file_sha256: str
    format: str
    size_bytes: int
    suggested_entity_type: str
    total_rows: int
    columns_found: List[str]
    suggested_mapping: Dict[str, str]
    preview_rows: List[Dict[str, Any]]

class ImportPlanRequest(BaseModel):
    job_id: int
    entity_type: str
    column_mapping: Dict[str, str]

class ImportPlanResponse(BaseModel):
    job_id: int
    entity_type: str
    summary: Dict[str, int]  # {new, changed, unchanged, conflict, invalid, skipped, duplicate_in_file}
    diff_preview: List[Dict[str, Any]]
    validation_errors: List[Dict[str, Any]]

class ImportConfirmRequest(BaseModel):
    job_id: int
    skip_invalid_rows: bool = False

class ImportReportResponse(BaseModel):
    job_id: int
    filename: str
    status: str
    summary: Dict[str, int]
    completed_at: Optional[datetime] = None
    error_count: int

# Exports
class ExportCreateRequest(BaseModel):
    format: str = "csv"  # csv, json, zip
    entities: List[str] = ["deals", "conversations", "risk_assessments", "follow_up_actions", "routing_decisions", "audit_events", "findings"]
    filters: Optional[Dict[str, Any]] = None

class ExportFileItem(BaseModel):
    file_name: str
    entity: str
    record_count: int
    sha256: str
    size_bytes: int

class ExportManifestData(BaseModel):
    export_id: int
    exported_at: str
    format: str
    entities: List[str]
    applied_filters: Optional[Dict[str, Any]] = None
    app_version: str
    schema_version: str
    as_of: str
    synthetic_data: bool
    validation_status: str
    manifest_sha256: str
    files: List[ExportFileItem]

class ExportJobRead(OrmModel):
    id: int
    format: str
    entities: List[str]
    filters: Optional[Dict[str, Any]] = None
    status: str
    validation_status: str
    total_records: int = 0
    bundle_url: Optional[str] = None
    created_at: datetime
    manifest: Optional[Dict[str, Any]] = None
    files: List[ExportFileItem] = []

class ExportVerifyResponse(BaseModel):
    export_id: int
    status: str  # verified or tampered
    details: List[Dict[str, Any]]
    all_matched: bool

# Audit
class AuditEventRead(OrmModel):
    id: int
    occurred_at: datetime
    actor_id: Optional[int] = None
    actor_label: str
    event_type: str
    entity_type: str
    entity_id: Optional[int] = None
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    import_job_id: Optional[int] = None
    correlation_id: str

# Findings
class FindingItem(BaseModel):
    id: str
    title: str
    severity: str  # high, critical, medium
    description: str
    deal_id: Optional[int] = None
    deal_code: Optional[str] = None
    deal_name: Optional[str] = None
    account_name: Optional[str] = None
    evidence_refs: List[Dict[str, Any]]
    recommended_action: str

class FindingsReportResponse(BaseModel):
    generated_at: datetime
    as_of: datetime
    findings: List[FindingItem]
    difficult_routing_decision: Optional[Dict[str, Any]] = None

# Dashboard Metrics
class DashboardMetricsResponse(BaseModel):
    as_of: datetime
    total_open_pipeline_value: float
    total_open_deals: int
    at_risk_deals_count: int
    high_priority_conversations_count: int
    overdue_follow_ups_count: int
    risk_distribution: Dict[str, int]  # Low, Medium, High, Critical
    stage_distribution: Dict[str, Dict[str, Any]]  # count and value per stage
    recent_activities: List[ActivityRead]
    team_performance: List[Dict[str, Any]]  # [{rep_name, open_deals, overdue_actions, completed_actions}]
    recent_alerts: List[AlertRead]
    what_should_i_do_today: List[FollowUpActionRead]
