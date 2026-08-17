import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { CATEGORIES } from '../constants.js'
import { Field, TextInput, NumberInput, TextArea, Select } from '../components/forms/Field.jsx'
import NegotiationBriefCard from '../components/NegotiationBriefCard.jsx'

export default function NegotiationBriefPage() {
  const [vendors, setVendors] = useState([])
  const [vendorId, setVendorId] = useState('')
  const [category, setCategory] = useState(CATEGORIES[0])
  const [contextDescription, setContextDescription] = useState(
    'Annual advisory contract renews in 30 days. Deciding whether to renew, and on what terms.'
  )
  const [currentValue, setCurrentValue] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => { api.listVendors().then(setVendors).catch(() => {}) }, [])

  const vendorOptions = [{ value: '', label: 'Select vendor...' }, ...vendors.map((v) => ({ value: v.vendor_id, label: `${v.vendor_id} — ${v.name}` }))]

  const submit = async () => {
    setError(null)
    setSubmitting(true)
    try {
      const res = await api.proposeNegotiationBrief({
        vendor_id: vendorId, category, context_description: contextDescription,
        current_annual_value_usd: currentValue ? Number(currentValue) : undefined,
      })
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl mb-1">Negotiation Brief</h1>
      <p className="text-ink-muted text-sm mb-6 max-w-3xl">
        Strategy prep for a human negotiator — not a decision, nothing to approve. Grounded in
        BATNA, a reasoned ZOPA estimate, and an integrative ("win-win") trade menu across non-price
        issues, using this vendor's real performance history and standard contract terms. Deliberately
        does not show a numeric win-probability — that needs real negotiation-outcome history to be
        honest, not a guess.
      </p>

      <div className="grid gap-4 max-w-2xl mb-5">
        <Field label="Vendor">
          <Select options={vendorOptions} value={vendorId} onChange={(e) => setVendorId(e.target.value)} />
        </Field>
        <Field label="Category">
          <Select options={CATEGORIES} value={category} onChange={(e) => setCategory(e.target.value)} />
        </Field>
        <Field label="Situation" hint="What's coming up — a renewal, a high-value negotiation, a performance issue.">
          <TextArea rows={3} value={contextDescription} onChange={(e) => setContextDescription(e.target.value)} />
        </Field>
        <Field label="Current annual value (USD, optional)">
          <NumberInput value={currentValue} onChange={(e) => setCurrentValue(e.target.value)} />
        </Field>
      </div>

      <button
        onClick={submit}
        disabled={submitting || !vendorId || !contextDescription.trim()}
        className="font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40"
      >
        {submitting ? 'Preparing brief... (takes ~30s, this is deliberate reasoning)' : 'Prepare negotiation brief'}
      </button>

      {error && <p className="text-accent text-sm mt-4 font-mono">{error}</p>}

      {result && (
        <section className="mt-8 border border-rule p-5">
          <NegotiationBriefCard brief={result.brief} sources={result.sources} agentId={result.agent_id} usage={result.usage} />
        </section>
      )}
    </div>
  )
}
