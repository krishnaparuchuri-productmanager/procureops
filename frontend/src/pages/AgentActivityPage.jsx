import { useEffect, useState } from 'react'
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
        and how many policy/vendor sections it retrieved before answering. This is the same data behind
        every decision card, as a running feed.
      </p>

      {!traces && <p className="text-ink-muted font-mono text-sm">Loading...</p>}
      {traces && traces.length === 0 && <p className="text-ink-muted font-mono text-sm">No agent runs yet.</p>}

      <div className="divide-y divide-rule">
        {traces && traces.map((t) => (
          <div key={t.id} className="py-3">
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
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
