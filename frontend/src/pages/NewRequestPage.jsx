import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'

const TABS = [
  { key: 'requisition', label: 'Requisition Intake' },
  { key: 'sourcing', label: 'Sourcing / Quote Comparison' },
  { key: 'invoice', label: 'Invoice Verification' },
  { key: 'inventory', label: 'Inventory Management' },
]

const EXAMPLES = {
  requisition: {
    raw_text:
      "Need 5 replacement laptops for the design team, budget code IT-4021, roughly $1,300 each from Meridian Compute Supply. I'm the requester and this is within my own sign-off limit.",
  },
  sourcing: {
    description: '50 enterprise laptops for the engineering org refresh.',
    category: 'IT Hardware & Software',
    quotes: [
      { vendor_id: 'V-001', unit_price: 1180, qty: 50, tax_pct: 7.0, freight_flat: 900, duty_flat: 0, lead_time_days: 12 },
      { vendor_id: 'V-016', unit_price: 1210, qty: 50, tax_pct: 7.0, freight_flat: 300, duty_flat: 0, lead_time_days: 9 },
      { vendor_id: 'V-007', unit_price: 1150, qty: 50, tax_pct: 7.0, freight_flat: 1100, duty_flat: 0, lead_time_days: 14 },
    ],
  },
  invoice: {
    po: { po_id: 'PO-5003', vendor_id: 'V-001', line_items: [{ sku: 'LAPTOP-ENT-11', qty: 10, unit_price: 1180.0 }], issue_date: '2026-06-08' },
    grn: { grn_id: 'GRN-5003', po_id: 'PO-5003', line_items: [{ sku: 'LAPTOP-ENT-11', qty_received: 10 }], received_date: '2026-06-15' },
    invoice: { invoice_id: 'INV-5003', po_id: 'PO-5003', vendor_id: 'V-001', line_items: [{ sku: 'LAPTOP-ENT-11', qty: 10, unit_price: 1265.0 }], tax: 885.5, freight: 0, total: 13535.5, invoice_date: '2026-06-17' },
  },
  inventory: {
    sku_record: {
      sku: 'SWITCH-24P', description: '24-port network switch', category: 'IT Hardware & Software',
      current_stock: 3, reorder_point: 6, avg_daily_usage: 0.3, lead_time_days: 14, preferred_vendor_id: 'V-007',
    },
  },
}

export default function NewRequestPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('requisition')
  const [raw, setRaw] = useState(JSON.stringify(EXAMPLES.requisition, null, 2))
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const switchTab = (key) => {
    setTab(key)
    setRaw(JSON.stringify(EXAMPLES[key], null, 2))
    setResult(null)
    setError(null)
  }

  const submit = async () => {
    setError(null)
    setSubmitting(true)
    try {
      const body = JSON.parse(raw)
      let res
      if (tab === 'requisition') res = await api.proposeRequisition(body)
      if (tab === 'sourcing') res = await api.proposeSourcing({ sourcing_case_id: `SRC-${Date.now()}`, ...body })
      if (tab === 'invoice') res = await api.proposeInvoice({ match_id: `TWM-${Date.now()}`, ...body })
      if (tab === 'inventory') res = await api.proposeInventory(body)
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl mb-1">New Request</h1>
      <p className="text-ink-muted text-sm mb-6">
        Calls the real specialist pipeline (RAG + LLM tool call). Edit the example JSON below or paste your own,
        then submit — the resulting proposal lands in the Decision Queue.
      </p>

      <div className="flex gap-1 mb-6 font-mono text-xs uppercase tracking-wide">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => switchTab(t.key)}
            className={`px-3 py-2 border-b-2 transition-colors ${
              tab === t.key ? 'text-accent border-accent' : 'text-ink-muted border-transparent hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <textarea
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        rows={16}
        spellCheck={false}
        className="w-full bg-paper-deep border border-rule px-3 py-3 font-mono text-xs leading-relaxed"
      />

      {error && <p className="text-accent text-sm mt-3 font-mono">{error}</p>}

      <button
        onClick={submit}
        disabled={submitting}
        className="mt-4 font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40"
      >
        {submitting ? 'Running agent...' : 'Submit'}
      </button>

      {result && (
        <section className="mt-8 border border-rule p-5">
          <h2 className="font-mono text-xs uppercase tracking-wider text-ink-muted mb-3">Proposal Created</h2>
          <pre className="font-mono text-xs whitespace-pre-wrap break-words mb-4">{JSON.stringify(result.assessment, null, 2)}</pre>
          <button
            onClick={() => navigate(`/decisions/${result.decision_id}`)}
            className="font-mono text-xs uppercase tracking-wider text-accent hover:underline"
          >
            View decision &rarr;
          </button>
        </section>
      )}
    </div>
  )
}
