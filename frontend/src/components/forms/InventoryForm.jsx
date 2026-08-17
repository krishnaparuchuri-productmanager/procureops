import { useState } from 'react'
import { Field, TextInput, NumberInput, Select } from './Field.jsx'
import { CATEGORIES } from '../../constants.js'

const initial = {
  sku: 'SWITCH-24P', description: '24-port network switch', category: CATEGORIES[0],
  currentStock: 3, reorderPoint: 6, avgDailyUsage: 0.3, leadTimeDays: 14, preferredVendorId: 'V-007',
}

export default function InventoryForm({ vendors, onSubmit, submitting }) {
  const [f, setF] = useState(initial)
  const set = (key) => (e) => setF((s) => ({ ...s, [key]: e.target.value }))

  const vendorOptions = [{ value: '', label: 'Select vendor...' }, ...vendors.map((v) => ({ value: v.vendor_id, label: `${v.vendor_id} — ${v.name}` }))]
  const canSubmit = f.sku && f.preferredVendorId

  const submit = () => {
    onSubmit({
      sku_record: {
        sku: f.sku, description: f.description, category: f.category,
        current_stock: Number(f.currentStock), reorder_point: Number(f.reorderPoint),
        avg_daily_usage: Number(f.avgDailyUsage), lead_time_days: Number(f.leadTimeDays),
        preferred_vendor_id: f.preferredVendorId,
      },
    })
  }

  return (
    <div>
      <p className="text-sm text-ink-muted mb-5">
        In production, stock levels and usage rates come from the warehouse management system — the
        agent proposes a reorder point/quantity the same way it would from the fields below. It never
        issues a PO directly; a proposal still routes through the standard requisition workflow.
      </p>

      <div className="grid sm:grid-cols-2 gap-4 max-w-2xl">
        <Field label="SKU"><TextInput value={f.sku} onChange={set('sku')} /></Field>
        <Field label="Description"><TextInput value={f.description} onChange={set('description')} /></Field>
        <Field label="Category"><Select options={CATEGORIES} value={f.category} onChange={set('category')} /></Field>
        <Field label="Preferred vendor"><Select options={vendorOptions} value={f.preferredVendorId} onChange={set('preferredVendorId')} /></Field>
        <Field label="Current stock"><NumberInput value={f.currentStock} onChange={set('currentStock')} /></Field>
        <Field label="Reorder point"><NumberInput value={f.reorderPoint} onChange={set('reorderPoint')} /></Field>
        <Field label="Avg daily usage"><NumberInput value={f.avgDailyUsage} onChange={set('avgDailyUsage')} step="0.1" /></Field>
        <Field label="Vendor lead time (days)"><NumberInput value={f.leadTimeDays} onChange={set('leadTimeDays')} /></Field>
      </div>

      <button
        onClick={submit}
        disabled={submitting || !canSubmit}
        className="mt-5 font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40"
      >
        {submitting ? 'Running agent...' : 'Check reorder status'}
      </button>
    </div>
  )
}
