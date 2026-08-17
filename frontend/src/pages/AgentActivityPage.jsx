import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import AgentBadge from '../components/AgentBadge.jsx'

export default function AgentActivityPage() {
  const [traces, setTraces] = useState(null)

  useEffect(() => { api.getTraces(100).then(setTraces) }, [])

  return (
    <div>
      <h1 className="text-3xl mb-1">Agent Activity</h1>
      <p className="text-ink-muted text-sm mb-6">
        Every specialist call, in order — which agent ran, how long it took, how many tokens it used,
        and how many policy/vendor sections it retrieved before answering. Click a row for the full
        decision — reasoning, cited sources, and the review action if it's still pending.
      </p>

      {!traces && <p className="text-ink-muted font-mono text-sm">Loading...</p>}
      {traces && traces.length === 0 && <p className="text-ink-muted font-mono text-sm">No agent runs yet.</p>}

      <div className="divide-y divide-rule">
        {traces && traces.map((t) => {
          const Row = t.decision_id ? Link : 'div'
          const rowProps = t.decision_id ? { to: `/decisions/${t.decision_id}` } : {}
          return (
            <Row
              key={t.id}
              {...rowProps}
              className={`block py-3 -mx-2 px-2 ${t.decision_id ? 'hover:bg-paper-deep transition-colors cursor-pointer' : ''}`}
            >
              <div className="flex items-center justify-between gap-4 mb-1">
                <AgentBadge agentId={t.agent_id} usage={t} />
                <span className="font-mono text-[10px] text-ink-muted whitespace-nowrap">
                  {new Date(t.timestamp).toLocaleString()}
                </span>
              </div>
              <p className="text-sm text-ink-muted truncate">{t.user_input}</p>
              <p className="font-mono text-[10px] text-ink-muted mt-1">
                {t.retrieved_chunk_count} source{t.retrieved_chunk_count === 1 ? '' : 's'} retrieved
                {t.error && <span className="text-accent"> · error: {t.error}</span>}
                {t.decision_id && <span className="text-accent"> · view decision →</span>}
              </p>
            </Row>
          )
        })}
      </div>
    </div>
  )
}
