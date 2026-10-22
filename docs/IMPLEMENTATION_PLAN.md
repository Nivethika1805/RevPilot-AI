# RevPilot AI — Implementation Plan
**Evidence-Driven Revenue Intelligence Inbox**

## 1. Executive Summary & Goals
RevPilot AI is a production-grade, evidence-driven B2B revenue intelligence inbox for sales managers and RevOps teams. It bridges conversation data, sales activities, CRM records, and risk assessments into an actionable cockpit with complete traceability from every finding to its exact source evidence.

Key Architectural Guarantees:
- **Zero Hallucination / Deterministic AI Core:** Pure-function, rule-based engines for risk scoring, routing, and action deduction that run deterministically with or without an LLM. Missing data evaluates to `unknown` (0 score) rather than risk.
- **Idempotency & Manual Correction Preservation:** Provenance-tracked field updates ensure re-imports cause zero duplicates and never overwrite manual corrections silently; conflicts are surfaced in a dedicated resolution lab.
- **Explainable Routing & Action Queue:** Transparent precedence rules (order -> specificity -> tie-break/review queue) with full alternative rejection logs and manual override persistence.
- **Verified Exports & Auditability:** Cryptographic SHA-256 manifests, formula-injection sanitization, and tamper verification.

---

## 2. Technology Stack & Versions
- **Backend:**
  - Python 3.13+
  - FastAPI 0.115+
  - Pydantic v2 (strict validation, OpenAPI schema generation)
  - SQLAlchemy 2.0+ (async & sync ORM, connection pooling, bound parameters)
  - Alembic 1.14+ (database schema migrations)
  - SQLite (WAL mode, local development & automated test suites) / PostgreSQL (production)
  - Pandas 2.2+ (tabular file parsing, sanitization, validation)
  - PyJWT & Passlib / Bcrypt (secure token authentication & role authorization)
  - Pytest & HTTPX TestClient (20+ automated scenarios)
- **Frontend:**
  - React 18+ / TypeScript 5+
  - Vite 6+
  - Tailwind CSS + Lucide Icons + Recharts
  - React Router DOM v6
  - TanStack Query v5 / Axios client
- **Infrastructure & Deployment:**
  - Multi-stage Dockerfiles (`backend`, `frontend`)
  - Docker Compose (`docker-compose.yml`)
  - Standalone Python smoke test (`scripts/smoke_test.py`)

---

## 3. Data Model & Entity Relationship Architecture
The data model uses SQLite/PostgreSQL-compatible types with explicit foreign keys, indexing, and audit/provenance links:

1. **`users`**: `id` (int PK), `email` (unique), `name`, `role` (admin, manager, rep, demo_evaluator), `team_id` (FK), `is_active`, `password_hash`, timestamps.
2. **`teams`**: `id` (int PK), `name` (unique), `responsibilities` (JSON), timestamps.
3. **`accounts`**: `id` (int PK), `external_id` (unique nullable), `name`, `industry`, `owner_user_id` (FK), `synthetic_flag` (bool), `normalized_name` (indexed), timestamps.
4. **`deals`**: `id` (int PK), `external_id` (unique nullable), `deal_code` (unique indexed, e.g. "DL-1001"), `account_id` (FK), `name`, `value`, `currency`, `stage`, `owner_user_id` (FK), `status` (open, won, lost), `expected_close_date`, `renewal_date`, `last_activity_at`, `next_activity_at`, `source_tracks_next_steps` (bool), `decision_maker_known` (bool nullable), timestamps.
5. **`conversations`**: `id` (int PK), `external_id` (unique nullable), `deal_id` (FK), `account_id` (FK), `assigned_user_id` (FK nullable), `type` (call, meeting, email, note), `occurred_at`, `summary`, `customer_intent`, `sentiment_label`, `sentiment_basis`, `urgency`, `priority`, `raw_text`, `source_file`, `source_record_ref`, `recommended_next_action`, `routing_status`, `content_hash`, timestamps.
6. **`evidence_excerpts`**: `id` (int PK), `conversation_id` (FK), `source_type`, `source_ref` (stable ID, e.g. "CALL-101#L14-L18"), `excerpt_text`, `start_offset`, `end_offset`, `occurred_at`, `extractor` ("rules" | "llm" | "manual"), timestamps.
7. **`conversation_findings`**: `id` (int PK), `conversation_id` (FK), `kind` (objection, unresolved_question, competitor_mention, follow_up_commitment, intent, sentiment_indicator), `label`, `status` (open, resolved), `evidence_id` (FK), `confidence` (float nullable), timestamps.
8. **`activities`**: `id` (int PK), `external_id` (unique nullable), `deal_id` (FK), `user_id` (FK), `type` (email_sent, customer_reply, meeting_scheduled, meeting_postponed, meeting_held, proposal_sent), `occurred_at`, `detail`, `source_ref`, timestamps.
9. **`risk_assessments`**: `id` (int PK), `deal_id` (FK), `assessed_at`, `as_of`, `rules_version`, `config_snapshot` (JSON), `score` (0-100), `category` (Low, Medium, High, Critical), `data_completeness_pct` (float), `confidence_note`, `trigger` (scheduled, import, manual, simulation_commit), `previous_assessment_id` (FK nullable), `is_current` (bool indexed), timestamps.
10. **`risk_signals`**: `id` (int PK), `assessment_id` (FK), `signal_code`, `state` (detected, not_detected, unknown), `severity`, `weight_applied`, `score_contribution`, `explanation`, `why_it_matters`, `evidence_ids` (JSON), timestamps.
11. **`risk_config`**: `id` (int PK), `signal_code`, `weight`, `threshold_params` (JSON), `enabled` (bool), `version` (int), timestamps.
12. **`alerts`**: `id` (int PK), `deal_id` (FK), `assessment_id` (FK), `status` (open, acknowledged, in_progress, resolved, reopened), `resolution_note`, `resolved_by` (FK nullable), `resolved_at`, `reopened_reason`, timestamps. (Enforces separation: Alert != Action != Risk score).
13. **`routing_rules`**: `id` (int PK), `name`, `priority_order` (int), `conditions` (JSON), `target_owner_user_id` (FK nullable), `target_team_id` (FK nullable), `priority_outcome`, `enabled` (bool), `version` (int), `specificity` (int), timestamps.
14. **`routing_decisions`**: `id` (int PK), `conversation_id` (FK), `decided_at`, `rules_evaluated` (JSON), `matched_rule_ids` (JSON), `winning_rule_id` (FK nullable), `recommended_owner_id` (FK nullable), `alternative_owner_id` (FK nullable), `priority`, `reason`, `evidence_ids` (JSON), `status` (recommended, accepted, overridden, unassigned_review), `override_by` (FK nullable), `override_owner_id` (FK nullable), `override_reason`, `is_current` (bool), timestamps.
15. **`follow_up_actions`**: `id` (int PK), `deal_id` (FK), `conversation_id` (FK nullable), `source` (recommended, manual), `title`, `reason`, `evidence_ids` (JSON), `priority`, `owner_user_id` (FK nullable), `due_date`, `status` (open, in_progress, completed, snoozed, dismissed), `snoozed_until`, `dismissed_reason`, `notes`, `dedupe_key` (unique per open action), `completed_at`, timestamps.
16. **`action_notes`**: `id` (int PK), `action_id` (FK), `author_id` (FK), `body`, `created_at`.
17. **`field_provenance`**: `id` (int PK), `entity_type`, `entity_id`, `field_name`, `source_value`, `current_value`, `previous_source_value`, `is_overridden` (bool), `last_update_source` (import, manual, resolution, seed), `last_import_job_id` (FK nullable), `updated_at`, UNIQUE(`entity_type`, `entity_id`, `field_name`).
18. **`field_conflicts`**: `id` (int PK), `entity_type`, `entity_id`, `field_name`, `current_value`, `incoming_value`, `source_baseline_value`, `import_job_id` (FK), `status` (pending, kept_manual, accepted_source, custom_value), `resolved_by` (FK nullable), `resolved_at`, `resolution_value`, timestamps.
19. **`import_jobs`**: `id` (int PK), `entity_type`, `filename`, `file_sha256`, `format`, `size_bytes`, `status` (uploaded, previewed, confirmed, completed, failed, rolled_back), `column_mapping` (JSON), `summary` (JSON), `created_by` (FK nullable), timestamps.
20. **`import_row_results`**: `id` (int PK), `job_id` (FK), `row_number`, `external_key`, `match_method` (external_id, natural_key, none), `outcome` (new, changed, unchanged, conflict, invalid, skipped, duplicate_in_file), `errors` (JSON), `changes` (JSON), `row_hash`.
21. **`export_jobs`**: `id` (int PK), `created_by` (FK nullable), `format`, `entities` (JSON), `filters` (JSON), `status`, `validation_status`, timestamps.
22. **`export_manifests`**: `id` (int PK), `export_job_id` (FK), `manifest_json` (JSON), `manifest_sha256`, `created_at`.
23. **`export_files`**: `id` (int PK), `export_job_id` (FK), `file_name`, `entity`, `record_count`, `sha256`, `size_bytes`, `path`.
24. **`audit_events`**: `id` (int PK), `occurred_at`, `actor_id` (FK nullable), `actor_label`, `event_type`, `entity_type`, `entity_id`, `before` (JSON), `after` (JSON), `reason`, `import_job_id` (FK nullable), `correlation_id` (indexed). Append-only.
25. **`findings_reports`**: `id` (int PK), `generated_at`, `as_of`, `items` (JSON with evidence refs), timestamps.

---

## 4. API Endpoints
- **Auth & System:**
  - `POST /api/auth/login` (returns JWT + role info)
  - `GET /api/auth/me` (current user profile, role, permissions)
  - `GET /api/health` (app version, schema version, DB connectivity status)
  - `GET /api/settings` & `PUT /api/settings/risk` (thresholds, weights, recompute trigger)
- **Dashboard & Intelligence:**
  - `GET /api/dashboard/metrics` (pipeline, at-risk, overdue actions, activity feed, risk distribution, stage breakdown, team indicators)
  - `GET /api/conversations` (search, filters, sort, pagination)
  - `GET /api/conversations/{id}` (full detail with findings, highlighted evidence excerpts, routing details)
  - `PATCH /api/conversations/{id}` (manual metadata update)
- **Deals & Risk:**
  - `GET /api/deals` (filtered list: risk category, stage, owner, value, completeness)
  - `GET /api/deals/{id}` (overview, risk breakdown, evidence panel with import links, decision timeline, actions, alert status)
  - `PATCH /api/deals/{id}` (provenance-tracked manual field update)
  - `GET /api/risk/deal/{deal_id}/history` (prior assessments with signal and score deltas)
  - `GET /api/risk/replay/{assessment_id}` (verify determinism against stored config snapshot)
  - `POST /api/risk/simulate` (pure what-if in-memory computation, zero mutations)
  - `POST /api/risk/simulate/commit` (explicit commitment of hypothetical changes)
- **Alerts & Actions:**
  - `POST /api/alerts/{id}/transition` (Open -> Acknowledged -> In progress -> Resolved -> Reopened)
  - `GET /api/actions` (ranked "What Should I Do Today?" queue)
  - `POST /api/actions` (create manual action)
  - `PATCH /api/actions/{id}` (assign, change priority, complete, snooze with date, dismiss with required reason)
  - `POST /api/actions/{id}/notes` (add note)
  - `POST /api/actions/regenerate` (deduped auto-generation from signals and deadlines)
- **Routing Engine:**
  - `GET /api/routing/rules` & `POST /api/routing/rules` & `PUT /api/routing/rules/{id}`
  - `POST /api/routing/decide/{conversation_id}` (evaluate rules with precedence)
  - `POST /api/routing/override/{conversation_id}` (manual override with reason)
  - `GET /api/routing/review-queue` (ambiguous or unassigned conversations)
  - `POST /api/routing/dry-run` (test conversation input against active rule-set)
- **Import & Correction Lab:**
  - `POST /api/imports/upload` (file upload, format/size sniff, row count)
  - `POST /api/imports/preview` (column mapping suggestions, preview first 10 rows)
  - `POST /api/imports/plan` (classification of all rows: new, changed, unchanged, conflict, invalid, skipped)
  - `POST /api/imports/confirm` (atomic single-transaction commit, provenance updates, rollback on failure)
  - `GET /api/imports/{id}/report` & `GET /api/imports/{id}/errors.csv` (downloadable error report)
  - `GET /api/imports/conflicts` & `POST /api/imports/conflicts/{id}/resolve` (keep manual / accept source / custom)
  - `GET /api/imports/provenance/{entity_type}/{entity_id}` (field-level source vs manual log)
- **Export Center & Findings:**
  - `POST /api/exports/generate` (CSV/JSON generation, formula sanitization, SHA256 computing)
  - `GET /api/exports` & `GET /api/exports/{id}/download` & `GET /api/exports/{id}/manifest`
  - `POST /api/exports/{id}/verify` (cryptographic integrity and row count re-verification)
  - `GET /api/findings` (database-derived evidence findings & difficult routing decision)
  - `GET /api/findings/export` (Markdown / JSON / CSV)
- **Audit:**
  - `GET /api/audit` (filterable by actor, event type, entity, date range)

---

## 5. Engines & Business Rules

### 5.1 Risk Engine
- Deterministic pure function: `assess(deal, conversations, findings, activities, config, as_of_date) -> Assessment`
- Data completeness formula: `100 * (evaluated_knowable_signals / total_applicable_signals)`.
- Evaluated states:
  - `detected`: contributes defined weight to total score.
  - `not_detected`: 0 points.
  - `unknown`: 0 points, treated strictly as incomplete evidence, never as risk.
- Default Signals:
  1. `NO_RECENT_CUSTOMER_RESPONSE` (20 pts, threshold > 14 days without customer reply).
  2. `UNRESOLVED_PRICING_OBJECTION` (25 pts, open pricing finding with no resolving note).
  3. `REPEATED_POSTPONEMENT` (15 pts, >= 2 postponed meetings within 45 days).
  4. `MISSING_NEXT_STEP` (15 pts, only if source tracks next steps and `next_activity_at` is null).
  5. `UNRESOLVED_PRODUCT_OR_IMPLEMENTATION_CONCERN` (15 pts, open technical/product objection).
  6. `APPROACHING_DEADLINE` (15 pts, close or renewal date within 30 days while other high-risk signals exist).
  7. `REPEATED_CUSTOMER_CONCERN` (10 pts, same objection category raised across >= 2 conversations).
  8. `MISSING_DECISION_MAKER` (10 pts, `decision_maker_known == False`).

### 5.2 Routing Engine Precedence
1. Lowest `priority_order` wins (e.g. 1 precedes 10).
2. If tied, highest `specificity` (number of matched condition clauses) wins.
3. If tied on order and specificity:
   - If both recommend the same owner, that owner wins.
   - If they recommend different owners, route to `unassigned_review` queue. No arbitrary owner selection.
4. Manual overrides take absolute precedence and remain untouched by re-routing runs.

### 5.3 Import & Provenance Reconciliation Policy
- Tracked fields retain: `source_value`, `previous_source_value`, `current_value`, `is_overridden`, `last_update_source`.
- Manual Edit: `current_value = manual_val`, `is_overridden = True`, `last_update_source = 'manual'`.
- Incoming Import:
  - If not overridden: update `current_value` and `source_value`.
  - If overridden and incoming == previous `source_value`: no-op, silent preserve.
  - If overridden and incoming != previous `source_value` and incoming != `current_value`: conflict detected, store in `field_conflicts`, preserve manual `current_value`.
  - If overridden and incoming == `current_value`: auto-agree, set `is_overridden = False`.
- Idempotency: exact identical file hash + row hash yields 0 updates and unchanged `updated_at`.

---

## 6. Testing Strategy
20 named automated integration and unit test scenarios:
1. `test_dashboard_metrics_match_database`
2. `test_search_and_filtering_accuracy`
3. `test_risk_signals_contain_valid_source_references`
4. `test_risk_engine_determinism`
5. `test_missing_evidence_evaluates_to_unknown_not_risk`
6. `test_routing_precedence_order_and_specificity`
7. `test_ambiguous_routing_enters_unassigned_review_queue`
8. `test_manual_routing_override_preserved_on_rerun`
9. `test_reimport_identical_dataset_creates_zero_duplicates`
10. `test_unchanged_imports_cause_no_updates_or_audits`
11. `test_new_source_values_do_not_silently_overwrite_manual_corrections`
12. `test_conflicting_values_surfaced_and_resolvable`
13. `test_failed_malformed_import_rolls_back_atomic_transaction`
14. `test_export_files_match_database_records`
15. `test_export_manifest_hashes_and_tamper_detection`
16. `test_audit_event_logging_for_key_actions`
17. `test_alert_resolution_does_not_mutate_risk_score`
18. `test_what_if_simulation_zero_mutation_and_commit_works`
19. `test_findings_report_contains_three_evidenced_findings_and_rejected_decision`
20. `test_deployed_smoke_test_suite`

---

## 7. Execution Stages & Timeline
- **Stage 1 (Now):** Workspace inspection & implementation plan.
- **Stage 2:** Foundation setup (backend models, Alembic migrations, reproducible seed data, /api/health).
- **Stage 3:** Core business logic (risk engine, routing, action queue, evidence linking, inbox).
- **Stage 4:** Data reliability (import wizard, provenance, conflict resolution, exports with manifests, audit trail).
- **Stage 5:** Differentiated features (deal cockpit, decision replay, what-if simulator, findings report).
- **Stage 6:** Testing, layout polish (desktop, tablet, mobile), frontend validation.
- **Stage 7:** Deployment configuration (Docker, compose, smoke test verification).
- **Stage 8:** Submission package (README, example exports, presentation deck, demo script, findings document).
