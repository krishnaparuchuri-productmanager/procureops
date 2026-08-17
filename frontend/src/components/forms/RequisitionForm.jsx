import { useState } from 'react'
import { Field, TextArea, TextInput } from './Field.jsx'

const EXAMPLE = "Need 5 replacement laptops for the design team, budget code IT-4021, roughly $1,300 each from Meridian Compute Supply. I'm the requester and this is within my own sign-off limit."

export default function RequisitionForm({ onSubmit, submitting }) {
  const [rawText, setRawText] = useState(EXAMPLE)
  const [requisitionId, setRequisitionId] = useState('')

  return (
    <div>
      <p className="text-sm text-ink-muted mb-5">
        In production this arrives as a free-text request from an intake form, Slack, or email —
        the Requisition Intake agent parses it directly, the same way it would parse the text below.
      </p>
      <div className="grid gap-4 max-w-2xl">
        <Field label="Requisition text" hint="Write it the way a requester actually would — category, vendor, and budget code don't need to be labeled.">
          <TextArea rows={5} value={rawText} onChange={(e) => setRawText(e.target.value)} />
        </Field>
        <Field label="Requisition ID (optional)" hint="Leave blank to auto-generate.">
          <TextInput value={requisitionId} onChange={(e) => setRequisitionId(e.target.value)} placeholder="REQ-2026-0142" />
        </Field>
      </div>
      <button
        onClick={() => onSubmit({ raw_text: rawText, requisition_id: requisitionId || undefined })}
        disabled={submitting || !rawText.trim()}
        className="mt-5 font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40"
      >
        {submitting ? 'Running agent...' : 'Submit requisition'}
      </button>
    </div>
  )
}
