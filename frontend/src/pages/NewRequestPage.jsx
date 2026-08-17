import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import RequisitionForm from '../components/forms/RequisitionForm.jsx'
import SourcingForm from '../components/forms/SourcingForm.jsx'
import InvoiceForm from '../components/forms/InvoiceForm.jsx'
import InventoryForm from '../components/forms/InventoryForm.jsx'

const TABS = [
  { key: 'requisition', label: 'Requisition Intake', source: 'an intake form, Slack, or email' },
  { key: 'sourcing', label: 'Sourcing / Quote Comparison', source: 'an RFQ tool or vendor portal' },
  { key: 'invoice', label: 'Invoice Verification', source: 'the ERP and vendor AP systems' },
  { key: 'inventory', label: 'Inventory Management', source: 'the warehouse management system' },
]

export default function NewRequestPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('requisition')
  const [vendors, setVendors] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => { api.listVendors().then(setVendors).catch(() => {}) }, [])

  const switchTab = (key) => {
    setTab(key)
    setResult(null)
    setError(null)
  }

  const submit = async (body) => {
    setError(null)
    setSubmitting(true)
    try {
      let res
      if (tab === 'requisition') res = await api.proposeRequisition(body)
      if (tab === 'sourcing') res = await api.proposeSourcing({ sourcing_case_id: `SRC-${Date.now()}`, ...body })
      if (tab === 'invoice') res = await api.proposeInvoice(body)
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
      <h1 className="text-3xl mb-1">Simulate an Incoming Request</h1>
      <p className="text-ink-muted text-sm mb-6 max-w-3xl">
        ProcureOps doesn't collect requests from people directly — each specialist normally receives
        structured data pushed from an upstream system. This page simulates that inbound data so you
        can see an agent's real reasoning (RAG-grounded, live LLM call) without needing those
        integrations wired up. Whatever you submit here lands in the Decision Queue exactly like a
        real inbound request would.
      </p>

      <div className="flex flex-wrap gap-1 mb-2 font-mono text-xs uppercase tracking-wide">
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
      <p className="text-xs text-ink-muted mb-6 normal-case">
        Normally sourced from: <span className="font-mono">{TABS.find((t) => t.key === tab).source}</span>
      </p>

      {tab === 'requisition' && <RequisitionForm onSubmit={submit} submitting={submitting} />}
      {tab === 'sourcing' && <SourcingForm vendors={vendors} onSubmit={submit} submitting={submitting} />}
      {tab === 'invoice' && <InvoiceForm vendors={vendors} onSubmit={submit} submitting={submitting} />}
      {tab === 'inventory' && <InventoryForm vendors={vendors} onSubmit={submit} submitting={submitting} />}

      {error && <p className="text-accent text-sm mt-4 font-mono">{error}</p>}

      {result && (
        <section className="mt-8 border border-rule p-5">
          <h2 className="font-mono text-xs uppercase tracking-wider text-ink-muted mb-3">Agent Response</h2>
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
