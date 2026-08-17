import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

export default function AuditLogPage() {
  const [entries, setEntries] = useState(null)

  useEffect(() => { api.getAudit(100).then(setEntries) }, [])

  return (
    <div>
      <h1 className="text-3xl mb-1">Audit Log</h1>
      <p className="text-ink-muted text-sm mb-6">
        INSERT-only. No update or delete endpoint exists for this table anywhere in the codebase.
      </p>

      {!entries && <p className="text-ink-muted font-mono text-sm">Loading...</p>}

      <div className="divide-y divide-rule">
        {entries && entries.map((e) => (
          <div key={e.id} className="py-3 flex items-start gap-4">
            <span className="font-mono text-[10px] text-ink-muted whitespace-nowrap pt-0.5">
              {new Date(e.event_time).toLocaleString()}
            </span>
            <div className="min-w-0 flex-1">
              <span className="font-mono text-xs uppercase tracking-wider text-accent mr-2">{e.action}</span>
              <span className="font-mono text-xs text-ink-muted">{e.actor}</span>
              {e.reason_code && <span className="font-mono text-[10px] text-ink-muted ml-2">[{e.reason_code}]</span>}
              <pre className="text-[11px] font-mono text-ink-muted mt-1 whitespace-pre-wrap break-words">
                {e.payload}
              </pre>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
