"""
schema.py — SQL CREATE TABLE statements for ProcureOps.

Conventions follow sop-deviation-review/backend/db/schema.py: explicit column
types, CHECK constraints, parameterized queries everywhere these tables are
touched. Two tables here are new relative to the GMP/MedAssist precedent —
decision_reviews and policy_versions — because those verticals never needed
per-transaction maker-checker or policy-snapshot-at-decision-time. See
docs/ARCHITECTURE.md for the rationale.
"""

# ---------------------------------------------------------------------------
# vendors — Approved Vendor Master, loaded from data/cases/vendors.json
# ---------------------------------------------------------------------------
CREATE_VENDORS_TABLE = """
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id        TEXT    PRIMARY KEY,          -- e.g. "V-001"
    name             TEXT    NOT NULL,
    category         TEXT    NOT NULL,
    approval_status  TEXT    NOT NULL              -- "approved" | "not_approved"
                     CHECK (approval_status IN ('approved', 'not_approved')),
    certifications   TEXT    NOT NULL DEFAULT '[]', -- JSON array of {name, expiry_date}
    on_time_pct      REAL,
    defect_rate_pct  REAL,
    note             TEXT
);
"""

# ---------------------------------------------------------------------------
# policy_versions — immutable, timestamped snapshots of the Procurement
# Policy Manual and DOA Matrix. A material edit inserts a new row and sets
# superseded_at on the row it replaces; nothing is ever edited in place.
# ---------------------------------------------------------------------------
CREATE_POLICY_VERSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS policy_versions (
    id              TEXT    PRIMARY KEY,           -- UUID v4
    doc_type        TEXT    NOT NULL               -- "procurement_policy_manual" | "doa_matrix"
                    CHECK (doc_type IN ('procurement_policy_manual', 'doa_matrix')),
    version         TEXT    NOT NULL,               -- e.g. "2026-06-01"
    content         TEXT    NOT NULL,               -- full immutable snapshot (markdown)
    effective_at    TEXT    NOT NULL,
    superseded_at   TEXT,                           -- NULL = currently active
    created_by      TEXT    NOT NULL,
    created_at      TEXT    NOT NULL
);
"""

# ---------------------------------------------------------------------------
# decision_reviews — maker-checker for domain decisions (vendor selection,
# invoice verdict, reorder action). proposed_by is always an agent_id;
# reviewed_by is always a human identity — the two live in disjoint identity
# spaces, which is what makes "agent cannot be its own checker" a structural
# guarantee rather than a name-matching rule enforced at the API layer.
# Vendor Selection and Invoice Verdict rows are ALWAYS created with
# decision=NULL (pending) — no code path auto-approves those two.
# ---------------------------------------------------------------------------
CREATE_DECISION_REVIEWS_TABLE = """
CREATE TABLE IF NOT EXISTS decision_reviews (
    id                  TEXT    PRIMARY KEY,        -- UUID v4
    decision_type       TEXT    NOT NULL
                        CHECK (decision_type IN ('vendor_selection', 'invoice_verdict', 'reorder_action', 'requisition_intake')),
    entity_ref          TEXT    NOT NULL,            -- sourcing_case_id / invoice_id / sku / requisition_id
    proposed_by         TEXT    NOT NULL,            -- agent_id, e.g. "procureops-sourcing"
    proposed_at         TEXT    NOT NULL,
    proposal            TEXT    NOT NULL,            -- JSON: the agent's structured recommendation
    reason_code         TEXT    NOT NULL,
    policy_version_id   TEXT    NOT NULL REFERENCES policy_versions(id),
    doa_version_id      TEXT    NOT NULL REFERENCES policy_versions(id),
    auto_cleared        INTEGER NOT NULL DEFAULT 0   -- 1 = threshold-based auto-clear (only requisition_intake / reorder_action)
                        CHECK (auto_cleared IN (0, 1)),
    reviewed_by         TEXT,                        -- NULL until a human decides; NULL forever if auto_cleared=1
    reviewed_at         TEXT,
    decision            TEXT CHECK (decision IN ('approved', 'rejected')),
    checker_reason      TEXT,
    trace_id            TEXT                         -- FK → traces.id, the LLM call that produced the proposal
);
"""

# ---------------------------------------------------------------------------
# traces — one row per specialist invocation, mirrors sop-deviation-review's
# traces table with an added agent_id column since ProcureOps runs 5 agents.
# ---------------------------------------------------------------------------
CREATE_TRACES_TABLE = """
CREATE TABLE IF NOT EXISTS traces (
    id               TEXT    PRIMARY KEY,           -- UUID v4
    agent_id         TEXT    NOT NULL,               -- "procureops-router" | "-requisition" | "-sourcing" | "-invoice" | "-inventory"
    timestamp        TEXT    NOT NULL,
    user_input       TEXT    NOT NULL,
    retrieved_chunks TEXT,                           -- JSON array of chunk_ids used
    prompt_version   TEXT    NOT NULL DEFAULT 'v1',
    model_output     TEXT,
    latency_ms       INTEGER,
    input_tokens     INTEGER,
    output_tokens    INTEGER,
    error            TEXT
);
"""

# ---------------------------------------------------------------------------
# audit_log — INSERT-only. No UPDATE or DELETE statement anywhere in the
# codebase references this table. Every agent decision, every human
# override, every escalation, every policy_versions write gets a row.
# ---------------------------------------------------------------------------
CREATE_AUDIT_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id           TEXT    PRIMARY KEY,               -- UUID v4
    event_time   TEXT    NOT NULL,
    actor        TEXT    NOT NULL,                   -- agent_id or human identity
    action       TEXT    NOT NULL,                   -- e.g. "DECISION_PROPOSED", "DECISION_REVIEWED", "POLICY_VERSION_CREATED"
    reason_code  TEXT,
    payload      TEXT    NOT NULL DEFAULT '{}'        -- JSON, full before/after context
);
"""

# ---------------------------------------------------------------------------
# eval_results — one row per (golden case, model_tag) per eval run.
# 8 dimensions, each 0-10 (LLM-as-judge), matching the AgentOps-level
# convention (agentops/backend/seed.py EVAL_DIMENSIONS), not the older
# 4-dimension/0-2 convention used inside sop-deviation-review's own runner.
# ---------------------------------------------------------------------------
CREATE_EVAL_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS eval_results (
    id                              TEXT    PRIMARY KEY,     -- UUID v4
    case_id                         TEXT    NOT NULL,
    run_id                          TEXT    NOT NULL,
    model_tag                       TEXT    NOT NULL DEFAULT 'actual',  -- "actual" | "baseline_always_auto_approve"
    policy_doa_citation             REAL    NOT NULL DEFAULT 0 CHECK (policy_doa_citation BETWEEN 0 AND 10),
    discrepancy_severity_classification REAL NOT NULL DEFAULT 0 CHECK (discrepancy_severity_classification BETWEEN 0 AND 10),
    exception_resolution_quality    REAL    NOT NULL DEFAULT 0 CHECK (exception_resolution_quality BETWEEN 0 AND 10),
    compliance_fraud_flag           REAL    NOT NULL DEFAULT 0 CHECK (compliance_fraud_flag BETWEEN 0 AND 10),
    escalation_behavior             REAL    NOT NULL DEFAULT 0 CHECK (escalation_behavior BETWEEN 0 AND 10),
    groundedness                    REAL    NOT NULL DEFAULT 0 CHECK (groundedness BETWEEN 0 AND 10),
    output_structure_clarity        REAL    NOT NULL DEFAULT 0 CHECK (output_structure_clarity BETWEEN 0 AND 10),
    vendor_neutrality               REAL    NOT NULL DEFAULT 0 CHECK (vendor_neutrality BETWEEN 0 AND 10),
    avg_score                       REAL    NOT NULL DEFAULT 0,
    overall_pass                    INTEGER NOT NULL DEFAULT 0 CHECK (overall_pass IN (0, 1)),
    notes                           TEXT,
    created_at                      TEXT    NOT NULL
);
"""

# ---------------------------------------------------------------------------
# policy_drift_flags — query-time findings, not mutations. Computed by
# comparing decision_reviews.policy_version_id against the currently active
# policy_versions row for that doc_type. Persisted here so a human can mark
# one reviewed without needing to touch the immutable decision it's about.
# ---------------------------------------------------------------------------
CREATE_POLICY_DRIFT_FLAGS_TABLE = """
CREATE TABLE IF NOT EXISTS policy_drift_flags (
    id               TEXT    PRIMARY KEY,           -- UUID v4
    decision_id      TEXT    NOT NULL REFERENCES decision_reviews(id),
    doc_type         TEXT    NOT NULL,
    cited_version_id TEXT    NOT NULL REFERENCES policy_versions(id),
    current_version_id TEXT  NOT NULL REFERENCES policy_versions(id),
    detected_at      TEXT    NOT NULL,
    resolved_at      TEXT,                          -- NULL = still open
    resolved_by      TEXT,
    resolution_note  TEXT
);
"""

ALL_TABLES = [
    ("vendors",             CREATE_VENDORS_TABLE),
    ("policy_versions",     CREATE_POLICY_VERSIONS_TABLE),
    ("decision_reviews",    CREATE_DECISION_REVIEWS_TABLE),
    ("traces",              CREATE_TRACES_TABLE),
    ("audit_log",           CREATE_AUDIT_LOG_TABLE),
    ("eval_results",        CREATE_EVAL_RESULTS_TABLE),
    ("policy_drift_flags",  CREATE_POLICY_DRIFT_FLAGS_TABLE),
]
