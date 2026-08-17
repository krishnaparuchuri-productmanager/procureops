import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client.js'
import RequisitionForm from '../components/forms/RequisitionForm.jsx'
import SourcingForm from '../components/forms/SourcingForm.jsx'
import SourcingStrategyForm from '../components/forms/SourcingStrategyForm.jsx'
import InvoiceForm from '../components/forms/InvoiceForm.jsx'
import InventoryForm from '../components/forms/InventoryForm.jsx'
import DecisionCard from '../components/DecisionCard.jsx'
import AskProcureOps from '../components/AskProcureOps.jsx'

const TABS = [
  { key: 'requisition', label: 'Requisition Intake', source: 'an intake form, Slack, or email', decisionType: 'requisition_intake' },
  { key: 'sourcing_strategy', label: 'Sourcing Strategy', source: 'a category owner or budget review', decisionType: 'sourcing_strategy' },
  { key: 'sourcing', label: 'Sourcing / Quote Comparison', source: 'an RFQ tool or vendor portal', decisionType: 'vendor_selection' },
  { key: 'invoice', label: 'Invoice Verification', source: 'the ERP and vendor AP systems', decisionType: 'invoice_verdict' },
  { key: 'inventory', label: 'Inventory Management', source: 'the warehouse management system', decisionType: 'reorder_action' },
]

const TAB_KEYS = TABS.map((t) => t.key)

export default function NewRequestPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialTab = TAB_KEYS.includes(searchParams.get('tab')) ? searchParams.get('tab') : 'requisition'
  const [tab, setTab] = useState(initialTab)
  const [vendors, setVendors] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [handoffText, setHandoffText] = useState(null)
  const [handoffKey, setHandoffKey] = useState(0)

  useEffect(() => { api.listVendors().then(setVendors).catch(() => {}) }, [])

  useEffect(() => {
    if (searchParams.get('tab')) {
      document.getElementById('specialist-forms')?.scrollIntoView({ behavior: 'smooth' })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const switchTab = (key) => {
    setTab(key)
    setResult(null)
    setError(null)
  }

  const handleHandoff = (taskType, text) => {
    setTab(taskType)
    setResult(null)
    setError(null)
    if (taskType === 'sourcing' || taskType === 'sourcing_strategy') {
      setHandoffText(text)
      setHandoffKey((k) => k + 1)
    }
    document.getElementById('specialist-forms')?.scrollIntoView({ behavior: 'smooth' })
  }

  const submit = async (body) => {
    setError(null)
    setSubmitting(true)
    try {
      let res
      if (tab === 'requisition') res = await api.proposeRequisition(body)
      if (tab === 'sourcing_strategy') res = await api.proposeSourcingStrategy(body)
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

      <AskProcureOps vendors={vendors} onHandoff={handleHandoff} />

      <h2 id="specialist-forms" className="text-xl mb-1 scroll-mt-20">Or go straight to a specialist</h2>
      <p className="text-ink-muted text-sm mb-4">Fill in a form directly — same specialists, no routing step.</p>

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
      {tab === 'sourcing_strategy' && (
        <SourcingStrategyForm key={handoffKey} onSubmit={submit} submitting={submitting} initialSpendDescription={handoffText} />
      )}
      {tab === 'sourcing' && (
        <SourcingForm key={handoffKey} vendors={vendors} onSubmit={submit} submitting={submitting} initialDescription={handoffText} />
      )}
      {tab === 'invoice' && <InvoiceForm vendors={vendors} onSubmit={submit} submitting={submitting} />}
      {tab === 'inventory' && <InventoryForm vendors={vendors} onSubmit={submit} submitting={submitting} />}

      {error && <p className="text-accent text-sm mt-4 font-mono">{error}</p>}

      {result && (
        <section className="mt-8 border border-rule p-5">
          <DecisionCard
            decisionType={TABS.find((t) => t.key === tab).decisionType}
            proposal={result.assessment}
            sources={result.sources}
            agentId={result.agent_id}
            usage={result.usage}
            vendors={vendors}
          />
          <button
            onClick={() => navigate(`/decisions/${result.decision_id}`)}
            className="mt-5 font-mono text-xs uppercase tracking-wider text-accent hover:underline"
          >
            View in Decision Queue &rarr;
          </button>
        </section>
      )}
    </div>
  )
}
