# ProcureOps — Architecture Note

Reviewed and confirmed with the product owner before implementation began. This
document is the durable record of that review; the chat conversation it came
from is not.

## Relationship to the existing AgentOps backbone

Three repos exist today: `agentops` (the governance platform — agent registry,
lifecycle state machine, eval-gated promotion), `sop-deviation-review` (GMP
vertical, FastAPI + SQLite backend with real RAG), `medassist-ai` (Cloudflare
Worker + React SPA, no backend of its own). ProcureOps is a fourth, separate
repo, structured like `sop-deviation-review` — it's the vertical that needs
its own RAG, its own DB, and its own domain logic, unlike MedAssist.

ProcureOps's 5 agents (Router + 4 specialists) register in AgentOps like
MedAssist's 6 do, for lifecycle tracking (Proposed → Under Review → Approved →
...). That mechanism is untouched.

## Two separate maker-checker mechanisms

**AgentOps' `approval_requests` table** governs *agent lifecycle* — promoting
an agent from Under Review to Approved. Unchanged, reused as-is.

**ProcureOps' `decision_reviews` table** (new) governs *domain decisions* — a
specific vendor recommendation, invoice verdict, or reorder proposal. This
axis didn't exist anywhere in the codebase before ProcureOps.

Note: while auditing the existing `agentops/backend/main.py` `decide_approval`
endpoint, we found it does not actually enforce `proposed_by != reviewed_by`
in code, despite `DECISIONS.md` D-02 claiming this is enforced "at the API
level." Neither the endpoint nor the frontend form checks it. ProcureOps does
not replicate this gap — see enforcement below. Patching the AgentOps endpoint
itself was considered and explicitly deferred as out of scope for this effort.

## `decision_reviews` — maker-checker for domain decisions

```
decision_type   IN ('vendor_selection', 'invoice_verdict', 'reorder_action', 'requisition_intake')
entity_ref      sourcing_case_id / invoice_id / sku / requisition_id
proposed_by     always an agent_id (e.g. "procureops-sourcing")
reviewed_by     always a human identity, NULL until reviewed
policy_version_id / doa_version_id   FK -> policy_versions, set at proposal time
auto_cleared    1 = threshold-based auto-clear; ONLY requisition_intake / reorder_action ever set this
decision        'approved' | 'rejected' | NULL (pending)
```

**Enforcement, in `routes/decisions.py::decide_review`:**
- `vendor_selection` and `invoice_verdict` rows are *always* created with
  `auto_cleared=0` — enforced unconditionally inside `_create_decision`,
  regardless of what the caller passes. No code path can self-approve either.
- `reviewed_by` is rejected with `409` if it's in the fixed `AGENT_IDS` set or
  equals `proposed_by` — a real check, not an assumption that agent-id and
  human-identity namespaces happen never to collide.
- Already-decided or already-auto-cleared rows return `409` on a second review
  attempt.

## Audit log

Same shape and guarantee as `agentops.audit_log` (INSERT-only, no UPDATE/DELETE
endpoint anywhere), instantiated in ProcureOps' own DB (`observability/audit.py`)
rather than depending on a live call to the central platform for every write.

## Policy snapshot

```
policy_versions: id, doc_type ('procurement_policy_manual' | 'doa_matrix'),
                 version, content, effective_at, superseded_at, created_by
```

A material edit inserts a new row and sets `superseded_at` on the row it
replaces — nothing is ever edited in place. Every `decision_reviews` row
stores `policy_version_id` and `doa_version_id` as an immutable snapshot
reference, set at proposal time from whichever version has `superseded_at IS
NULL` at that moment (`routes/policy.py::get_active_version`).

**Reason codes** — fixed enum (`agents/common.py::REASON_CODES`), defined in
Procurement Policy Manual Section 11, constrained via each specialist's tool
schema so the value is never free text.

**Policy drift detector** — `GET /decisions/{id}/drift`. Query-time computed
comparison of a decision's cited `policy_version_id`/`doa_version_id` against
the currently active ones; writes a `policy_drift_flags` row only if they
differ. Never mutates the `decision_reviews` row it's flagging — the finding
lives beside the immutable record, not inside it.

## RAG — four corpora, one TF-IDF index

`retrieval.py` extends `sop-deviation-review`'s `##`-header chunking + TF-IDF
+ cosine-similarity approach (no vector DB) across:

- `procurement_policy_manual`, `doa_matrix`, `contract_terms` — markdown docs
  under `backend/data/policy/`
- `vendor_master` — one markdown profile per vendor under
  `backend/data/vendor_master/`, chunked the same way

All four are indexed together; every chunk carries a `corpus` tag so a caller
can restrict a query to one (`search_docs(query, corpus="vendor_master")`).

## Eval harness — 8 dimensions, 0-10, LLM-as-judge

Matches the convention actually found in `agentops/backend/seed.py`
(`EVAL_DIMENSIONS`, 8 dims, 0-10, gate `avg_score >= 6.0 AND
escalation_behavior >= 7.0`) rather than `sop-deviation-review`'s own
4-dimension/0-2 runner. Dimensions: `policy_doa_citation`,
`discrepancy_severity_classification`, `exception_resolution_quality`,
`compliance_fraud_flag`, `escalation_behavior`, `groundedness`,
`output_structure_clarity`, `vendor_neutrality`.

Baseline for comparison is `always_auto_approve`, not `always_escalate` — the
dangerous default in procurement is approving everything (false negative =
money out the door same-day), the inverse of GMP's conservative
always-escalate baseline.
