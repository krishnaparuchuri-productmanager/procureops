import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import { decisionStatusBadge } from '../components/Badge.jsx'

export default function DecisionDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [decision, setDecision] = useState(null)
  const [drift, setDrift] = useState(null)
  const [reviewedBy, setReviewedBy] = useState('')
  const [checkerReason, setCheckerReason] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const load = () => api.getDecision(id).then(setDecision).catch((e) => setError(e.message))

  useEffect(() => { load() }, [id])

  const proposal = decision ? JSON.parse(decision.proposal) : null

  const handleReview = async (decisionValue) => {
    setError(null)
    setSubmitting(true)
    try {
      await api.reviewDecision(id, { reviewed_by: reviewedBy, decision: decisionValue, checker_reason: checkerReason })
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDrift = async () => {
    const result = await api.checkDrift(id)
    setDrift(result)
  }

  if (error && !decision) return <p className="text-accent font-mono text-sm">{error}</p>
  if (!decision) return <p className="text-ink-muted font-mono text-sm">Loading...</p>

  return (
    <div>
      <button onClick={() => navigate('/')} className="font-mono text-xs uppercase tracking-wider text-ink-muted hover:text-ink mb-6">
        &larr; Back to queue
      </button>

      <div className="flex items-center gap-3 mb-2">
        <h1 className="text-3xl">{decision.entity_ref}</h1>
        {decisionStatusBadge(decision)}
      </div>
      <p className="font-mono text-xs uppercase tracking-wider text-ink-muted mb-8">
        {decision.decision_type} &middot; proposed by {decision.proposed_by} &middot; {new Date(decision.proposed_at).toLocaleString()}
      </p>

      <section className="border border-rule p-5 mb-6">
        <h2 className="font-mono text-xs uppercase tracking-wider text-ink-muted mb-3">Agent Proposal</h2>
        <pre className="font-mono text-xs whitespace-pre-wrap break-words">{JSON.stringify(proposal, null, 2)}</pre>
      </section>

      <section className="border border-rule p-5 mb-6">
        <h2 className="font-mono text-xs uppercase tracking-wider text-ink-muted mb-3">Governance</h2>
        <dl className="grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-ink-muted">Reason code</dt>
          <dd className="font-mono">{decision.reason_code}</dd>
          <dt className="text-ink-muted">Policy version cited</dt>
          <dd className="font-mono text-xs">{decision.policy_version_id}</dd>
          <dt className="text-ink-muted">DOA version cited</dt>
          <dd className="font-mono text-xs">{decision.doa_version_id}</dd>
        </dl>
        <button
          onClick={handleDrift}
          className="mt-4 font-mono text-xs uppercase tracking-wider border border-rule px-3 py-1.5 hover:border-ink transition-colors"
        >
          Check policy drift
        </button>
        {drift && (
          <p className="mt-3 text-sm">
            {drift.drifted ? (
              <span className="text-accent">
                Drifted — this decision cites a policy version older than current ({drift.flags.length} flag(s)).
              </span>
            ) : (
              <span className="text-ink-muted">No drift — cited versions match the current active policy.</span>
            )}
          </p>
        )}
      </section>

      {!decision.auto_cleared && decision.decision === null && (
        <section className="border border-accent p-5">
          <h2 className="font-mono text-xs uppercase tracking-wider text-accent mb-3">
            Human Review Required — this decision was proposed by an agent and cannot self-approve
          </h2>
          <div className="grid gap-3 max-w-md">
            <label className="text-xs font-mono uppercase tracking-wide text-ink-muted">
              Your name (reviewer)
              <input
                type="text"
                value={reviewedBy}
                onChange={(e) => setReviewedBy(e.target.value)}
                placeholder="e.g. Jane Procurement Lead"
                className="mt-1 w-full bg-paper border border-rule px-2 py-1.5 font-sans text-sm text-ink normal-case"
              />
            </label>
            <label className="text-xs font-mono uppercase tracking-wide text-ink-muted">
              Reason
              <textarea
                value={checkerReason}
                onChange={(e) => setCheckerReason(e.target.value)}
                rows={2}
                className="mt-1 w-full bg-paper border border-rule px-2 py-1.5 font-sans text-sm text-ink normal-case"
              />
            </label>
          </div>
          {error && <p className="text-accent text-sm mt-3">{error}</p>}
          <div className="flex gap-3 mt-4">
            <button
              disabled={!reviewedBy || submitting}
              onClick={() => handleReview('approved')}
              className="font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Approve
            </button>
            <button
              disabled={!reviewedBy || submitting}
              onClick={() => handleReview('rejected')}
              className="font-mono text-xs uppercase tracking-wider border border-accent text-accent px-4 py-2 hover:bg-accent hover:text-paper transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Reject
            </button>
          </div>
        </section>
      )}

      {decision.decision && (
        <section className="border border-rule p-5">
          <h2 className="font-mono text-xs uppercase tracking-wider text-ink-muted mb-2">Review Record</h2>
          <p className="text-sm">
            <strong>{decision.reviewed_by}</strong> {decision.decision} this on{' '}
            {new Date(decision.reviewed_at).toLocaleString()}
            {decision.checker_reason && <> — &ldquo;{decision.checker_reason}&rdquo;</>}
          </p>
        </section>
      )}
    </div>
  )
}
