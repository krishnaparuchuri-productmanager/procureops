import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { DECISION_TYPE_LABELS } from '../constants.js'

const SEVERITY_STYLE = {
  high: 'text-accent border-accent',
  medium: 'text-ink-soft border-ink-soft',
  low: 'text-ink-muted border-rule',
}

function timeAgo(iso) {
  const ms = Date.now() - new Date(iso).getTime()
  const hrs = Math.floor(ms / 3600000)
  if (hrs < 1) return 'less than an hour ago'
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function NotificationsPanel() {
  const [data, setData] = useState(null)

  useEffect(() => { api.getNotifications().then(setData).catch(() => {}) }, [])

  if (!data) return null

  if (data.pending_count === 0) {
    return (
      <div className="border border-rule p-4 mb-8 text-sm text-ink-muted">
        All caught up — no decisions waiting on review.
      </div>
    )
  }

  const borderClass = data.high_severity_count > 0 ? 'border-accent' : 'border-rule-strong'

  return (
    <div className={`border ${borderClass} p-4 mb-8`}>
      <div className="flex items-center justify-between mb-3">
        <p className="font-mono text-xs uppercase tracking-wider">
          Needs Attention
          <span className={data.high_severity_count > 0 ? 'text-accent' : 'text-ink-muted'}>
            {' '}&middot; {data.pending_count} pending
            {data.high_severity_count > 0 && ` · ${data.high_severity_count} high severity`}
          </span>
        </p>
        <Link to="/decisions" className="font-mono text-[10px] uppercase tracking-wider text-ink-muted hover:text-ink">
          View all &rarr;
        </Link>
      </div>

      {data.drifted_decision_ids.length > 0 && (
        <p className="text-xs text-accent mb-3">
          {data.drifted_decision_ids.length} pending decision{data.drifted_decision_ids.length === 1 ? '' : 's'} cite
          {' '}a policy version that has since changed.
        </p>
      )}

      <div className="divide-y divide-rule">
        {data.pending.map((p) => (
          <Link
            key={p.id}
            to={`/decisions/${p.id}`}
            className="flex items-center justify-between gap-4 py-2 hover:bg-paper-deep transition-colors -mx-1 px-1"
          >
            <div className="min-w-0 flex items-center gap-2">
              <span className={`font-mono text-[9px] uppercase tracking-wider border px-1 py-0.5 flex-shrink-0 ${SEVERITY_STYLE[p.severity]}`}>
                {p.severity}
              </span>
              <span className="text-sm truncate">{DECISION_TYPE_LABELS[p.decision_type] || p.decision_type}</span>
              <span className="font-mono text-xs text-ink-muted truncate">{p.entity_ref}</span>
            </div>
            <span className="font-mono text-[10px] text-ink-muted flex-shrink-0">{timeAgo(p.proposed_at)}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
