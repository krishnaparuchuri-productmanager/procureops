import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

const DOC_LABELS = {
  procurement_policy_manual: 'Procurement Policy Manual',
  doa_matrix: 'Delegation of Authority Matrix',
}

export default function PolicyPage() {
  const [current, setCurrent] = useState(null)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => { api.getPolicyCurrent().then(setCurrent) }, [])

  return (
    <div>
      <h1 className="text-3xl mb-1">Active Policy</h1>
      <p className="text-ink-muted text-sm mb-6">
        Every decision stores a snapshot reference to the exact version shown here at the moment it was made —
        not a live pointer. Editing either document creates a new immutable version rather than mutating this one.
      </p>

      {!current && <p className="text-ink-muted font-mono text-sm">Loading...</p>}

      <div className="grid gap-4">
        {current && Object.entries(DOC_LABELS).map(([docType, label]) => {
          const version = current[docType]
          if (!version) return null
          const isOpen = expanded === docType
          return (
            <div key={docType} className="border border-rule">
              <button
                onClick={() => setExpanded(isOpen ? null : docType)}
                className="w-full flex items-center justify-between p-4 text-left"
              >
                <div>
                  <span className="font-serif text-lg mr-3">{label}</span>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">
                    v{version.version} &middot; effective {new Date(version.effective_at).toLocaleDateString()}
                  </span>
                </div>
                <span className="font-mono text-xs text-ink-muted">{isOpen ? '&minus;' : '+'}</span>
              </button>
              {isOpen && (
                <div className="border-t border-rule p-4 bg-paper-deep">
                  <pre className="whitespace-pre-wrap text-xs font-mono leading-relaxed max-h-96 overflow-y-auto">
                    {version.content}
                  </pre>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
