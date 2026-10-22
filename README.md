# RevPilot AI — Evidence-Driven Revenue Intelligence Inbox

> *"Know what happened. Understand why it matters. Decide what to do next."*

RevPilot AI is a production-grade revenue intelligence platform engineered for sales managers and RevOps leaders. It unifies conversation transcripts, customer emails, meeting notes, CRM pipeline records, and sales activity into an actionable, evidence-backed workspace.

Unlike traditional revenue tools that present opaque "AI scores" or invent unsubstantiated projections, RevPilot AI enforces **strict evidence-to-action traceability**: every detected risk signal, unresolved objection, and routing decision links directly to verbatim source excerpts with immutable character offsets and stable reference IDs.

---

## Key Differentiators & Principles

1. **Evidence-to-Action Traceability**: No finding exists in a vacuum. Every pricing objection, delayed response, and postponed meeting cites the exact line in the transcript or email (e.g., `CALL-2043#L2`), with timestamps and original speakers.
2. **Deterministic Risk Index (Not a Probability)**: Risk scores (0–100) are computed via pure deterministic functions. It is transparently presented as a **Rule-based risk index**, never as a pseudo-scientific actuarial probability of losing a deal.
3. **Absence of Proof is Not Proof of Risk**: When a source CRM does not track next steps or customer contact data is missing, the engine evaluates the signal as `unknown` (contributing 0 to the risk score) and transparently reduces the **Data Completeness %**. Missing data is never treated as proof of negative intent.
4. **Decoupled Alert Lifecycle**: Resolving an alert or marking a task done does *not* artificially lower the risk index. Risk recalculates only when new verified evidence arrives.
5. **Idempotent Multi-Source Ingestion & Provenance**: Re-importing identical files causes **zero updates** and **zero duplicate rows**. Manual edits by managers are protected via field-level provenance (`is_overridden`). Conflicting incoming updates are quarantined for manager resolution (`keep_manual`, `accept_source`, `custom_value`).
6. **Cryptographic Export Verification**: Exports in CSV and JSON formats include signed `manifest.json` packages with SHA-256 digests. Formula injection (`=`, `+`, `-`, `@`) is neutralized at generation time.
7. **Zero-LLM Core**: Full duplicate detection, risk scoring, precedence routing, and audit logging function deterministically with zero external LLM dependencies.

---

## Architecture Diagram

```mermaid
graph TD
    subgraph ClientLayer["Frontend Client (React 18 + TS + Tailwind + Vite)"]
        UI_CC[Command Center]
        UI_Inbox[Intelligence Inbox]
        UI_Deals[Deals & Risk Cockpit]
        UI_Action[Action Queue]
        UI_Routing[Explainable Routing]
        UI_Import[Import & Correction Lab]
        UI_Replay[Decision Replay & Simulator]
        UI_Export[Export Center]
        UI_Audit[Immutable Audit Ledger]
    end

    subgraph APILayer["FastAPI Application Services (Python 3.11+)"]
        API_GW[FastAPI Router /api]
        Auth[JWT Auth & Public Demo Evaluator]
        Clock[Injectable Pinned Clock Service]
        RiskEng[Pure Risk Engine]
        RouteEng[Precedence Routing Engine]
        ExtractEng[Span Extractor (Rules / LLM)]
        ImportEng[11-Stage Idempotent Import Pipeline]
        ExportEng[Cryptographic Export & Manifest Service]
        AuditEng[Append-Only Audit Logger]
    end

    subgraph DataLayer["Storage & Ledger"]
        DB[(PostgreSQL / SQLite WAL)]
        FileStore[Export Disk Bundles]
    end

    UI_CC --> API_GW
    UI_Inbox --> API_GW
    UI_Deals --> API_GW
    UI_Action --> API_GW
    UI_Routing --> API_GW
    UI_Import --> API_GW
    UI_Replay --> API_GW
    UI_Export --> API_GW
    UI_Audit --> API_GW

    API_GW --> Auth
    API_GW --> RiskEng
    API_GW --> RouteEng
    API_GW --> ExtractEng
    API_GW --> ImportEng
    API_GW --> ExportEng
    API_GW --> AuditEng

    RiskEng --> DB
    RouteEng --> DB
    ImportEng --> DB
    ExportEng --> FileStore
    AuditEng --> DB
```

---

## Tech Stack

- **Backend**: Python 3.11+ / 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 ORM, Alembic migrations, Pandas, Pytest, Uvicorn.
- **Database**: PostgreSQL 16 for containerized/production topologies; SQLite 3 with WAL mode and foreign key constraints enabled for local dev/testing.
- **Frontend**: React 18, TypeScript (Strict), Vite, Tailwind CSS, Lucide React, TanStack Query v5, Recharts, React Router v6.
- **Security & Integrity**: Passlib/Bcrypt password hashing, PyJWT, CSV formula injection sanitization (`'=`), SHA-256 cryptographic manifests.
- **DevOps**: Docker, multi-stage Dockerfiles, Docker Compose, Nginx reverse proxy.

---

## Getting Started (Local Development)

### Prerequisites
- Python 3.11+ (tested on Python 3.11, 3.12, and 3.13)
- Node.js 18+ & npm 9+
- Git

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Alembic migrations to apply initial 25-table schema
alembic upgrade head

# Seed reproducible synthetic dataset (idempotent)
python run_seed.py

# Start FastAPI server on port 8000
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be live at `http://127.0.0.1:8000`. OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install npm dependencies
npm install

# Start Vite development server with proxy to :8000
npm run dev
```

The web application will be accessible at `http://localhost:5173`.

---

## Environment Configuration

Configuration is managed via environment variables. See `.env.example` in root:

```ini
# Application Horizon
AS_OF_DATE=2026-10-20T00:00:00Z
APP_NAME="RevPilot AI"
VERSION=1.0.0
SCHEMA_VERSION=1.0.0

# Database
DATABASE_URL=sqlite:///./revpilot.db
# For PostgreSQL:
# DATABASE_URL=postgresql://revpilot:password@localhost:5432/revpilot

# Security & Demo Mode
SECRET_KEY=revpilot-super-secret-key-change-in-production
DEMO_MODE=true
CORS_ORIGINS=http://localhost:5173,http://localhost:80,http://127.0.0.1:8000

# Optional LLM API Key (deterministic rules extractor active by default)
LLM_API_KEY=
```

---

## Import Merge & Provenance Policy

RevPilot AI implements an **11-stage idempotent import pipeline**:
1. Upload & size check (max 5MB, `.csv` or `.json`).
2. Format sniffing (UTF-8, delimiter auto-detection, formula sanitation).
3. Header inspection and column mapping suggestions.
4. Type/enum validation and FK integrity checking.
5. Natural key & external ID resolution.
6. Normalized SHA-256 row hashing for duplicate detection.
7. Row-level classification: `new`, `changed`, `unchanged`, `conflict`, `invalid`, `duplicate_in_file`.
8. Field-level diff preview with provenance inspection.
9. Atomic single-transaction database commit (all-or-nothing rollback on error).
10. Execution of re-assessment triggers for affected deals.
11. Downloadable error report CSV for invalid rows.

### Field-Level Provenance & Conflict Rules:
For every tracked entity field, RevPilot stores:
`source_value`, `previous_source_value`, `current_value`, `is_overridden`, `last_update_source`, `updated_at`.

- **Rule A (Clean Source Update)**: Field is not overridden (`is_overridden=False`) and incoming != current -> `current_value` and `source_value` update to incoming value.
- **Rule B (Idempotent No-op)**: Incoming == current -> No database write executed (`updated_at` and audit counts remain unchanged).
- **Rule C (Preserved Manual Correction)**: Field was manually edited (`is_overridden=True`), and incoming source matches the baseline `source_value` -> Manual value is preserved silently without raising an unnecessary conflict.
- **Rule D (Quarantined Conflict)**: Field was manually edited, but incoming source differs from baseline `source_value` AND from `current_value` -> Manual value is held intact, and a `pending` conflict is recorded in `field_conflicts`.
- **Rule E (Auto-Agreement)**: Field was manually edited, and incoming source matches the current manual edit -> `is_overridden` is reset to `False` and conflict potential is cleared.

---

## Routing Precedence & Tie-Breaking Hierarchy

Conversations are routed to account owners or specialized teams according to transparent precedence:
1. **Precedence Rank**: Rules are evaluated in ascending order of `priority_order` (e.g., `#1 High-Urgency Pricing` evaluates before `#5 Standard Commercial`).
2. **Specificity Metric**: When two rules have identical `priority_order`, the rule with more matching conditions (higher `specificity`) wins.
3. **Deterministic Safety (Tie-Breaking)**: If tied rules recommend the *same* owner, that owner is assigned. If tied rules recommend *different* owners, the conversation automatically enters the **Unassigned Review Queue**. The system never guesses owners or breaks ties by internal IDs.
4. **Persistent Overrides**: Manual routing overrides take precedence over rule evaluations and are preserved across bulk re-routing runs.

---

## Risk Scoring Methodology & Limitations

RevPilot AI calculates a **Rule-based risk index (0–100)**:
- **Low Risk**: 0–24 pts
- **Medium Risk**: 25–49 pts
- **High Risk**: 50–74 pts
- **Critical Risk**: 75–100 pts

### Default Signals:
1. `NO_RECENT_CUSTOMER_RESPONSE` (+20 pts): Silence > 14 days.
2. `UNRESOLVED_PRICING_OBJECTION` (+25 pts): Open pricing objection without subsequent resolving evidence.
3. `REPEATED_POSTPONEMENT` (+15 pts): $\ge$ 2 postponements in 45 days.
4. `MISSING_NEXT_STEP` (+15 pts): `source_tracks_next_steps=True`, `next_activity_at=None`, and no open commitments.
5. `UNRESOLVED_PRODUCT_OR_IMPLEMENTATION_CONCERN` (+15 pts): Open technical/compliance objection.
6. `APPROACHING_DEADLINE` (+15 pts): Close or renewal within 30 days while other risks exist.
7. `REPEATED_CUSTOMER_CONCERN` (+10 pts): Same concern raised across $\ge$ 2 conversations.
8. `MISSING_DECISION_MAKER` (+10 pts): `decision_maker_known=False`.

> **Important Notice on Methodology**:
> The risk index is an explainable heuristic measure of detected friction points. **It is not an actuarial probability of deal loss.** A deal with a 75 index is not 75% likely to be lost; it indicates multiple active risk signals requiring sales management attention.

---

## Export Data Dictionary

Exports generated from the Export Center contain consistent column schemas sanitized against formula injection:

| File | Key Fields | Description |
| :--- | :--- | :--- |
| `deals.csv` | `deal_code`, `name`, `account_name`, `value`, `stage`, `status`, `risk_score`, `risk_category`, `expected_close_date` | Complete pipeline opportunity registry |
| `conversations.csv` | `source_record_ref`, `deal_code`, `type`, `occurred_at`, `summary`, `customer_intent`, `sentiment_label`, `routing_status`, `urgency` | Interaction transcripts and email summaries |
| `risk_assessments.csv` | `deal_code`, `score`, `category`, `data_completeness_pct`, `trigger`, `assessed_at` | Versioned assessment scorecards |
| `follow_up_actions.csv` | `deal_code`, `title`, `reason`, `priority`, `status`, `due_date` | Action queue tasks with evidence links |
| `audit_history.csv` | `event_id`, `occurred_at`, `actor_label`, `event_type`, `entity_type`, `entity_id`, `reason`, `correlation_id` | Immutable ledger of system state changes |
| `manifest.json` | `export_id`, `exported_at`, `total_records`, `validation_status`, `files` (with `sha256`, `size_bytes`) | Cryptographic verification descriptor |

---

## Automated Test Suite

Run the full suite of automated unit and scenario tests:

```bash
# Run backend pytest suite (22 tests)
cd backend
pytest -v tests/test_all_scenarios.py

# Run frontend Vitest suite (4 tests)
cd ../frontend
npm run test
```

### Verified Test Scenarios:
1. `test_dashboard_metrics_equal_database`: Metrics match independently calculated SQL queries.
2. `test_search_and_filtering_accuracy`: Multi-field filter validation.
3. `test_risk_signals_contain_source_references`: Verifies every signal points to an excerpt.
4. `test_risk_engine_determinism`: Identical inputs produce identical scores across runs.
5. `test_missing_evidence_is_unknown_not_risk`: Validates `unknown` adds 0 pts and lowers completeness.
6. `test_routing_precedence_order_and_specificity`: Precedence rule tie-breaking.
7. `test_ambiguous_routing_enters_unassigned_review_queue`: Prevents invented owners.
8. `test_manual_routing_override_preserved_on_rerun`: Protects manual assignments.
9. `test_reimport_identical_dataset_zero_duplicates`: 0 duplicates on re-import.
10. `test_unchanged_imports_cause_no_updates`: 0 DB writes on unchanged rows.
11. `test_new_source_values_do_not_silently_overwrite_manual_corrections`: Preserves overrides.
12. `test_conflicting_values_surfaced_and_resolvable`: Tests conflict resolution options.
13. `test_failed_malformed_import_rolls_back`: Atomic rollback verification.
14. `test_export_files_contain_expected_records`: Validates exported record contents.
15. `test_export_manifest_hashes_and_tamper_detection`: Verifies tamper detection flags alterations.
16. `test_audit_event_logging_for_key_actions`: Verifies append-only logging.
17. `test_alert_resolution_does_not_mutate_risk_score`: Verifies alert/risk separation.
18. `test_what_if_simulation_zero_mutation_and_commit`: Verifies simulation zero mutation.
19. `test_findings_report_contains_three_findings_and_difficult_routing`: Verifies live report.
20. `test_health_check_endpoint`: Verifies `/api/health` status.
21. `test_decision_replay_matching_and_mismatching_scores`: Verifies match vs mismatch flags.
22. `test_export_manifest_record_counts_agree`: Verifies manifest total matches file sum.

---

## Deployment (Docker Compose)

To run the complete stack containerized:

```bash
# From project root
docker compose -f deploy/docker-compose.yml up --build
```

- Nginx Frontend: `http://localhost:80`
- FastAPI Backend: `http://localhost:8000`
- PostgreSQL 16: `localhost:5432` (user: `revpilot`, db: `revpilot`)

### Production Deployment Topology
- **Frontend**: Deploy static bundle (`frontend/dist`) to Cloudflare Pages, Vercel, or Netlify. Set `VITE_API_BASE_URL` to backend domain.
- **Backend**: Deploy container (`deploy/Dockerfile.backend`) to Render, Fly.io, or Railway with `DATABASE_URL` pointing to managed Postgres (Neon, Supabase, or AWS RDS).
- **Smoke Test**: Run `python scripts/smoke_test.py --base-url https://your-backend-domain.com`.
