import { useState } from 'react'
import { Field, TextInput, NumberInput, Select } from './Field.jsx'
import { CATEGORIES } from '../../constants.js'

const emptyQuote = () => ({ vendor_id: '', unit_price: '', qty: '', tax_pct: '', freight_flat: '', duty_flat: '', lead_time_days: '' })

export default function SourcingForm({ vendors, onSubmit, submitting }) {
  const [description, setDescription] = useState('50 enterprise laptops for the engineering org refresh.')
  const [category, setCategory] = useState(CATEGORIES[0])
  const [quotes, setQuotes] = useState([
    { vendor_id: 'V-001', unit_price: 1180, qty: 50, tax_pct: 7.0, freight_flat: 900, duty_flat: 0, lead_time_days: 12 },
    { vendor_id: 'V-016', unit_price: 1210, qty: 50, tax_pct: 7.0, freight_flat: 300, duty_flat: 0, lead_time_days: 9 },
    { vendor_id: 'V-007', unit_price: 1150, qty: 50, tax_pct: 7.0, freight_flat: 1100, duty_flat: 0, lead_time_days: 14 },
  ])

  const vendorOptions = [{ value: '', label: 'Select vendor...' }, ...vendors.map((v) => ({ value: v.vendor_id, label: `${v.vendor_id} — ${v.name}` }))]

  const updateQuote = (i, field, value) =>
    setQuotes((qs) => qs.map((q, idx) => (idx === i ? { ...q, [field]: value } : q)))
  const addQuote = () => setQuotes((qs) => [...qs, emptyQuote()])
  const removeQuote = (i) => setQuotes((qs) => qs.filter((_, idx) => idx !== i))

  const canSubmit = description.trim() && quotes.length > 0 && quotes.every((q) => q.vendor_id && q.unit_price !== '' && q.qty !== '')

  const submit = () => {
    onSubmit({
      description,
      category,
      quotes: quotes.map((q) => ({
        vendor_id: q.vendor_id,
        unit_price: Number(q.unit_price),
        qty: Number(q.qty),
        tax_pct: Number(q.tax_pct || 0),
        freight_flat: Number(q.freight_flat || 0),
        duty_flat: Number(q.duty_flat || 0),
        lead_time_days: Number(q.lead_time_days || 0),
      })),
    })
  }

  return (
    <div>
      <p className="text-sm text-ink-muted mb-5">
        In production, competing quotes arrive from an RFQ tool or a vendor's e-procurement portal once
        a requisition clears the competitive-bidding threshold — the agent compares them the same way
        it would compare the rows below.
      </p>

      <div className="grid gap-4 max-w-2xl mb-6">
        <Field label="What's being sourced">
          <TextInput value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <Field label="Category">
          <Select options={CATEGORIES} value={category} onChange={(e) => setCategory(e.target.value)} />
        </Field>
      </div>

      <div className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-2">Competing quotes</div>
      <div className="overflow-x-auto border border-rule">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-rule text-left font-mono text-[10px] uppercase tracking-wide text-ink-muted">
              <th className="p-2">Vendor</th>
              <th className="p-2">Unit Price</th>
              <th className="p-2">Qty</th>
              <th className="p-2">Tax %</th>
              <th className="p-2">Freight $</th>
              <th className="p-2">Duty $</th>
              <th className="p-2">Lead Time (d)</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {quotes.map((q, i) => (
              <tr key={i} className="border-b border-rule last:border-0">
                <td className="p-2 min-w-[180px]">
                  <Select options={vendorOptions} value={q.vendor_id} onChange={(e) => updateQuote(i, 'vendor_id', e.target.value)} />
                </td>
                <td className="p-2 w-24"><NumberInput value={q.unit_price} onChange={(e) => updateQuote(i, 'unit_price', e.target.value)} /></td>
                <td className="p-2 w-20"><NumberInput value={q.qty} onChange={(e) => updateQuote(i, 'qty', e.target.value)} /></td>
                <td className="p-2 w-20"><NumberInput value={q.tax_pct} onChange={(e) => updateQuote(i, 'tax_pct', e.target.value)} /></td>
                <td className="p-2 w-24"><NumberInput value={q.freight_flat} onChange={(e) => updateQuote(i, 'freight_flat', e.target.value)} /></td>
                <td className="p-2 w-24"><NumberInput value={q.duty_flat} onChange={(e) => updateQuote(i, 'duty_flat', e.target.value)} /></td>
                <td className="p-2 w-24"><NumberInput value={q.lead_time_days} onChange={(e) => updateQuote(i, 'lead_time_days', e.target.value)} /></td>
                <td className="p-2">
                  <button onClick={() => removeQuote(i)} className="text-accent font-mono text-xs" title="Remove quote">×</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button onClick={addQuote} className="mt-2 font-mono text-xs uppercase tracking-wider text-ink-muted hover:text-ink">
        + Add quote
      </button>

      <div>
        <button
          onClick={submit}
          disabled={submitting || !canSubmit}
          className="mt-5 font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40"
        >
          {submitting ? 'Running agent...' : 'Submit for comparison'}
        </button>
      </div>
    </div>
  )
}
