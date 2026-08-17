# ProcureOps

A **Procurement Router + 4 Specialists** governance vertical for the AgentOps
multi-agent governance platform. Third vertical alongside GMP Deviation Review
and MediAssist — same governance backbone (maker-checker, INSERT-only audit
log, LLM-as-judge eval framework), extended with policy-snapshot-at-decision-time,
which neither of the other two verticals implements.

**All data is synthetic.** No real ERP (SAP/Oracle/NetSuite) or payment
integration — this is a governance-architecture demo against a realistic
procurement domain, not a working procurement system.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design
rationale, reviewed and confirmed before implementation began.

## What It Does

A Router classifies incoming requests and hands off to four specialists:

| Agent | Role | Model | Human-gated? |
|---|---|---|---|
| Router | Classifies request -> specialist | Haiku | n/a |
| Requisition Intake | DOA/budget validation, missing-field checks | Haiku | Threshold-based |
| Sourcing / Quote Comparison | Total-landed-cost vendor comparison | Sonnet | **Always** |
| Invoice Verification | Three-way match (PO/GRN/Invoice) | Sonnet | **Always** |
| Inventory Management | Reorder point/quantity proposals | Haiku | Threshold-based |

Sourcing and Invoice Verification touch money leaving the company — no
autonomous approval, ever. Every proposal from those two becomes a
`decision_reviews` row that stays `decision=NULL` until a human, who cannot
be the proposing agent, approves or rejects it.

## Governance

- **Maker-checker at the API level** — `POST /api/decisions/{id}/review`
  rejects with `409` if `reviewed_by` is an agent id or matches `proposed_by`.
- **INSERT-only audit log** — no UPDATE/DELETE endpoint anywhere in the codebase.
- **Policy snapshot at decision time** — every decision stores the exact
  `policy_version_id`/`doa_version_id` in force when it was made, plus a
  fixed-enum `reason_code`. A query-time drift detector (`GET
  /api/decisions/{id}/drift`) flags when a decision's cited version is older
  than current.
- **Eval-gated promotion** — 8 dimensions, 0-10 scale, LLM-as-judge. Gate:
  `avg_score >= 6.0 AND escalation_behavior >= 7.0`.

## Quickstart (Local)

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env    # add ANTHROPIC_API_KEY
python db/init_db.py
python seed/demo_seed.py
uvicorn main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

Run the eval suite (calls the Anthropic API for every case, both agents and judge):

```bash
python eval_runner.py
```

## Deployment

Not yet deployed. Mirrors the existing AgentOps verticals: FastAPI backend on
Railway (`backend/Dockerfile` + `railway.json`), frontend on Cloudflare Pages
(`frontend/wrangler.toml`).

```bash
# Backend (Railway) — connect the repo in the Railway dashboard, it builds
# from backend/Dockerfile automatically. Set ANTHROPIC_API_KEY as an env var.

# Frontend (Cloudflare Pages)
cd frontend && npm run build && npx wrangler deploy
```

The custom domain `procureops.krishnaparuchuri.com` is not yet created —
confirm the DNS record with Krishna before adding it.

## Folder Structure

```
procureops/
├── backend/
│   ├── main.py                  FastAPI app, CORS, router wiring
│   ├── retrieval.py              TF-IDF RAG over 4 corpora
│   ├── llm_client.py              Anthropic wrapper (Haiku + Sonnet)
│   ├── eval_runner.py            8-dimension LLM-as-judge eval harness
│   ├── agents/                   Router + 4 specialists (prompts, tool schemas)
│   ├── routes/                   decisions.py (maker-checker), policy.py
│   ├── observability/audit.py    INSERT-only audit log writer
│   ├── db/                       schema.py, init_db.py
│   ├── seed/                     demo_seed.py
│   └── data/
│       ├── policy/               Procurement Policy Manual, DOA Matrix, Contract Terms (RAG)
│       ├── vendor_master/        One profile per vendor (RAG)
│       └── cases/                Requisitions, quotes, PO/GRN/Invoice, inventory, golden eval set
├── frontend/
└── docs/ARCHITECTURE.md
```

*Built by Krishna Paruchuri. Product decisions are mine; implementation is AI-assisted.*
