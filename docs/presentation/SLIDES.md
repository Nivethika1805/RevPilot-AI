# RevPilot AI — Executive Slide Deck
## Evidence-Driven Revenue Intelligence Inbox
**Author:** RevPilot Engineering & Product Architecture Team  
**Date:** October 2026  
**Format:** 5-Slide Executive Overview (Markdown / Marp compatible)

---

## Slide 1: Problem Statement & Product Vision

### The Enterprise Revenue Dilemma
- **Black-Box Hallucinations**: Sales reps and managers do not trust black-box "AI scores" that lack source references.
- **Fragmented Truth**: Critical customer objections, delayed email responses, and postponement signals live in disjointed tools (call recorders, email inboxes, CRM tables).
- **Silent Data Overwrite**: CRM syncs overwrite manual corrections made by front-line sales managers, destroying local context.

### The RevPilot AI Vision
> *"Know what happened. Understand why it matters. Decide what to do next."*

- **Evidence-to-Action Engine**: Every risk signal, objection, and routing assignment links directly to immutable verbatim transcript excerpts (e.g., `CALL-2043#L2`).
- **Explainable Heuristics**: Pure, deterministic risk indexing (0–100) — transparently labeled as a heuristic measure of friction, not an actuarial probability.
- **Data Governance**: Field-level provenance protects manual corrections while preventing duplicate imports.

---

## Slide 2: Architecture & Technical Approach

### Decoupled, Deterministic Full-Stack System
- **Frontend**: React 18, TypeScript (Strict), Vite, Tailwind CSS, TanStack Query v5, Recharts.
- **Backend**: FastAPI (Python 3.11+), Pydantic v2, SQLAlchemy 2.0 ORM, Alembic migrations.
- **Storage**: PostgreSQL 16 for production / SQLite 3 WAL for zero-latency local development.
- **Pinned Temporal Horizon**: Injectable `Clock` service pins evaluation to `2026-10-20T00:00:00Z` to guarantee 100% reproducible test runs.

### Architectural Invariants
1. **Zero-LLM Core**: Full duplicate detection, risk indexing, precedence routing, and audit logging operate with zero external API dependencies.
2. **Absence of Proof $\ne$ Proof of Risk**: Missing tracking records contribute 0 to the risk index, reducing the **Data Completeness %** instead.
3. **Decoupled Alert State Machine**: Resolving an alert (`open` $\rightarrow$ `resolved`) audits manager workflow without artificially depressing the deal risk score.

---

## Slide 3: Unique Differentiators & Primary Findings

### Live Database Findings (October 2026 Horizon)
1. **Critical High-Value Pricing Stall (`DL-1001`)**:
   - $240,000 expansion opportunity (Northwind Logistics).
   - 21 days of customer silence coupled with explicit pushback (`CALL-2043#L2`: *"price is too high compared to what we budgeted"*).
   - Generated Action: Schedule VP-level commercial alignment with tiered billing.
2. **Pipeline Milestone Blindspot (7 Open Deals)**:
   - Audited $1.18M in pipeline where CRM tracks forward steps, yet `next_activity_at` is null with zero commitments.
3. **Quarantined Urgent Interaction (`CALL-2045`)**:
   - High-urgency hospital EHR compliance review held in Review Queue rather than guessing an unverified owner.

---

## Slide 4: The Difficult Routing Decision & Precedence Trade-Off

### Case Study: Interaction `EMAIL-2044` (Northwind Pricing Redline)
- **Dialogue Summary**: Northwind Finance requested a 15% across-the-board seat discount before executive signing.
- **The Conflict**:
  - **Rule #1 (High-Urgency Pricing Escalation)**: Matches `topic: pricing` + `urgency: critical`. Points to Marcus Vance (Pricing Lead). Priority: `1`, Specificity: `2`.
  - **Rule #4 (Standard Commercial Routing)**: Matches `topic: pricing`. Points to Elena Rostova (Commercial AE). Priority: `5`, Specificity: `1`.

### Architectural Resolution
```
                        [ Incoming EMAIL-2044 ]
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   Rule #1 (Priority 1, Spec 2)              Rule #4 (Priority 5, Spec 1)
   [ Marcus Vance - Pricing Lead ]           [ Elena Rostova - Commercial AE ]
              │                                         │
              └────────────────────┬────────────────────┘
                                   │
                       Precedence Hierarchy Applied:
                         Priority 1 < Priority 5
                                   │
                                   ▼
                 WINNER: Marcus Vance (Pricing Lead)
                 REJECTED: Elena Rostova (Lower Precedence)
```
- **Audited Rationale**: The decision log permanently records both the winning route and the rejected candidate, eliminating rep disputes and lost leads.

---

## Slide 5: Data Reliability Test Results & Next Steps

### Empirical Verification (Real Runs, Real Output)
- **Idempotent Re-Import**: 20 deals re-imported twice $\rightarrow$ **0 new rows, 20 unchanged, 0 DB updates**.
- **Provenance Preservation**: Re-importing source updates against overridden deal `DL-1005` preserved the manual value and surfaced a reviewable conflict.
- **Cryptographic Export Integrity**: 134 records exported with SHA-256 manifest. Tamper detection verified byte-level alteration detection.
- **Test Suite Results**:
  - **Backend (Pytest)**: **22 passed, 0 failed** in 6.64s.
  - **Frontend (Vitest)**: **4 passed, 0 failed** in 0.17s.
  - **Integration Smoke Test**: **7 endpoints passed, 0 failed**.

### Next Steps for Enterprise Rollout
1. Connect enterprise CRM webhooks (Salesforce / HubSpot REST APIs).
2. Activate optional schema-validated LLM extractor for long multi-speaker transcripts.
3. Deploy containerized topology to managed Kubernetes with PostgreSQL 16.
