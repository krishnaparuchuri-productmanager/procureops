export const CATEGORIES = [
  'IT Hardware & Software',
  'Office Supplies & Equipment',
  'Professional Services',
  'Raw Materials / Production Inputs',
  'Facilities & Maintenance',
  'Logistics & Freight',
]

// Fixed platform fact — which model tier each agent runs on. Not stored
// per-trace (it's a property of the agent, not a per-call variable).
export const AGENTS = {
  'procureops-router': { label: 'Router', model: 'Haiku', tier: 'haiku' },
  'procureops-requisition-intake': { label: 'Requisition Intake', model: 'Haiku', tier: 'haiku' },
  'procureops-sourcing': { label: 'Sourcing / Quote Comparison', model: 'Sonnet', tier: 'sonnet' },
  'procureops-sourcing-strategy': { label: 'Sourcing Strategy', model: 'Sonnet', tier: 'sonnet' },
  'procureops-invoice-verification': { label: 'Invoice Verification', model: 'Sonnet', tier: 'sonnet' },
  'procureops-inventory-management': { label: 'Inventory Management', model: 'Haiku', tier: 'haiku' },
  'procureops-negotiation-brief': { label: 'Negotiation Brief', model: 'Sonnet', tier: 'sonnet' },
  'procureops-contract-renewal': { label: 'Contract Renewal', model: 'Sonnet', tier: 'sonnet' },
}

export const DECISION_TYPE_LABELS = {
  vendor_selection: 'Vendor Selection',
  invoice_verdict: 'Invoice Verdict',
  requisition_intake: 'Requisition Intake',
  reorder_action: 'Reorder Action',
  sourcing_strategy: 'Sourcing Strategy',
  contract_renewal: 'Contract Renewal',
}

export const CORPUS_LABELS = {
  procurement_policy_manual: 'Procurement Policy Manual',
  doa_matrix: 'DOA Matrix',
  contract_terms: 'Standard Contract Terms',
  vendor_master: 'Vendor Master',
}
