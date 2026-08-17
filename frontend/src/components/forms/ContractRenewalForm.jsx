import { useState } from 'react'
import { Field, TextArea, NumberInput, Select } from './Field.jsx'
import WorkflowStepper from '../WorkflowStepper.jsx'

const STEPS = ['Renewal Due', 'Bounded-Autonomy Check', 'Specialist Review', 'Clear or Escalate']

export default function ContractRenewalForm({ vendors, onSubmit, submitting }) {
  const [vendorId, setVendorId] = useState('')
  const [currentValue, setCurrentValue] = useState('12000')
  const [proposedValue, setProposedValue] = useState('12300')
  const [contextDescription, setContextDescription] = useState(
    'Annual contract renews in 30 days. Vendor has confirmed the proposed terms; deciding whether this can clear automatically.'
  )

  const vendorOptions = [{ value: '', label: 'Select vendor...' }, ...vendors.map((v) => ({ value: v.vendor_id, label: `${v.vendor_id} — ${v.name}` }))]
  const selectedVendor = vendors.find((v) => v.vendor_id === vendorId)

  return (
    <div>
      <WorkflowStepper steps={STEPS} currentIndex={0} />
      <p className="text-sm text-ink-muted mb-5">
        Checks a proposed renewal against this vendor's category thresholds — a fixed set of numbers a
        company configures in advance (see <span className="font-mono">Autonomy Config</span>), evaluated as
        plain code, never by the agent's own judgment. Within the band, this clears on its own; outside it,
        a human decides. Either way, the specialist below writes the reasoning behind what happened.
      </p>
      <div className="grid gap-4 max-w-2xl">
        <Field label="Vendor">
          <Select options={vendorOptions} value={vendorId} onChange={(e) => setVendorId(e.target.value)} />
        </Field>
        {selectedVendor && (
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted -mt-2">
            Category: {selectedVendor.category}
          </p>
        )}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Current annual value (USD)">
            <NumberInput value={currentValue} onChange={(e) => setCurrentValue(e.target.value)} />
          </Field>
          <Field label="Proposed annual value (USD)">
            <NumberInput value={proposedValue} onChange={(e) => setProposedValue(e.target.value)} />
          </Field>
        </div>
        <Field label="Context" hint="Anything relevant a reviewer — human or the specialist below — should know.">
          <TextArea rows={3} value={contextDescription} onChange={(e) => setContextDescription(e.target.value)} />
        </Field>
      </div>
      <button
        onClick={() => onSubmit({
          vendor_id: vendorId, category: selectedVendor?.category,
          current_annual_value_usd: Number(currentValue), proposed_annual_value_usd: Number(proposedValue),
          context_description: contextDescription,
        })}
        disabled={submitting || !vendorId || !currentValue || !proposedValue || !contextDescription.trim()}
        className="mt-5 font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40"
      >
        {submitting ? 'Running rule check + specialist...' : 'Check this renewal'}
      </button>
    </div>
  )
}
