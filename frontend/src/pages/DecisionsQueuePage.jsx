import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { decisionStatusBadge } from '../components/Badge.jsx'
import { DECISION_TYPE_LABELS as TYPE_LABELS } from '../constants.js'

export default function DecisionsQueuePage() {
  const [decisions, setDecisions] = useState(null)
  const [pendingOnly, setPendingOnly] = useState(true)
  const [typeFilter, setTypeFilter] = useState('')
  const [error, setError] = useState(null)

  useEffect(() => {
    const params = {}
    if (pendingOnly) params.pending_only = 'true'
    if (typeFilter) params.decision_type = typeFilter
    api.listDecisions(params).then(setDecisions).catch((e) => setError(e.message))
  }, [pendingOnly, typeFilter])

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 border-b border-rule-strong pb-4">
        <div>
          <h1 className="text-3xl mb-1">Decision Queue</h1>
          <p className="text-ink-muted text-sm">
            Vendor Selection and Invoice Verdict decisions never auto-clear — they wait here
            until a human, who cannot be the proposing agent, approves or rejects them.
          </p>
        </div>
        <Link
          to="/new"
          className="font-mono text-xs uppercase tracking-wider border border-ink px-3 py-2 hover:bg-ink hover:text-paper transition-colors"
        >
          + Simulate Request
        </Link>
      </div>

      <div className="flex items-center gap-4 mb-6 font-mono text-xs uppercase tracking-wider">
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={pendingOnly} onChange={(e) => setPendingOnly(e.target.checked)} />
          Pending only
        </label>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="bg-paper border border-rule px-2 py-1"
        >
          <option value="">All types</option>
          {Object.entries(TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-accent font-mono text-sm">{error}</p>}
      {!decisions && !error && <p className="text-ink-muted font-mono text-sm">Loading...</p>}
      {decisions && decisions.length === 0 && (
        <p className="text-ink-muted font-mono text-sm">No decisions match this filter.</p>
      )}

      <div className="divide-y divide-rule">
        {decisions && decisions.map((d) => (
          <Link
            key={d.id}
            to={`/decisions/${d.id}`}
            className="flex items-center justify-between py-4 hover:bg-paper-deep transition-colors -mx-2 px-2"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">
                  {TYPE_LABELS[d.decision_type] || d.decision_type}
                </span>
                {decisionStatusBadge(d)}
              </div>
              <div className="font-serif text-lg">{d.entity_ref}</div>
              <div className="text-ink-muted text-xs font-mono">
                {d.proposed_by} &middot; {d.reason_code} &middot; {new Date(d.proposed_at).toLocaleString()}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
