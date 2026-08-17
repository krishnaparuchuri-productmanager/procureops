import { useState } from 'react'
import { Field, TextArea, NumberInput, Select } from './Field.jsx'
import { CATEGORIES } from '../../constants.js'
import WorkflowStepper from '../WorkflowStepper.jsx'

const STEPS = ['Trigger', 'Strategy', 'Bid Collection', 'Comparison & Award']

export default function SourcingStrategyForm({ onSubmit, submitting, initialSpendDescription }) {
  const [category, setCategory] = useState(CATEGORIES[0])
  const [spendDescription, setSpendDescription] = useState(
    initialSpendDescription ||
    "We keep buying laptops piecemeal every time someone joins the design team. We want a real strategy for the next 12 months instead of ad-hoc purchases."
  )
  const [budgetHint, setBudgetHint] = useState('45000')

  return (
    <div>
      <WorkflowStepper steps={STEPS} currentIndex={1} />
      <p className="text-sm text-ink-muted mb-5">
        For a spend question before any quotes exist — before an RFP is even drafted. The agent
        proposes a vendor shortlist, weighted evaluation criteria, and a single- vs multi-source
        recommendation. Once quotes come back, that goes to Sourcing / Quote Comparison, not here.
      </p>
      <div className="grid gap-4 max-w-2xl">
        <Field label="Category">
          <Select options={CATEGORIES} value={category} onChange={(e) => setCategory(e.target.value)} />
        </Field>
        <Field label="Describe the spend need" hint="Vague is fine — that's the point of this specialist.">
          <TextArea rows={4} value={spendDescription} onChange={(e) => setSpendDescription(e.target.value)} />
        </Field>
        <Field label="Rough budget estimate (USD, optional)" hint="Determines whether competitive bidding is required.">
          <NumberInput value={budgetHint} onChange={(e) => setBudgetHint(e.target.value)} />
        </Field>
      </div>
      <button
        onClick={() => onSubmit({
          category, spend_description: spendDescription,
          budget_hint_usd: budgetHint ? Number(budgetHint) : undefined,
        })}
        disabled={submitting || !spendDescription.trim()}
        className="mt-5 font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40"
      >
        {submitting ? 'Running agent...' : 'Propose sourcing strategy'}
      </button>
    </div>
  )
}
