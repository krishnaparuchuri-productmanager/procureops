import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { TextArea } from '../components/forms/Field.jsx'

const DOC_LABELS = {
  procurement_policy_manual: 'Procurement Policy Manual',
  doa_matrix: 'Delegation of Authority Matrix',
}

const today = () => new Date().toISOString().slice(0, 10)

export default function PolicyPage() {
  const [current, setCurrent] = useState(null)
  const [expanded, setExpanded] = useState(null)
  const [createdBy, setCreatedBy] = useState('')
  const [creatingFor, setCreatingFor] = useState(null)
  const [versionLabel, setVersionLabel] = useState('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const load = () => api.getPolicyCurrent().then(setCurrent)
  useEffect(() => { load() }, [])

  const startNewVersion = (docType, version) => {
    setError(null)
    setExpanded(null)
    setCreatingFor(docType)
    setVersionLabel(today())
    setContent(version.content)
  }

  const publish = async () => {
    setError(null)
    setSubmitting(true)
    try {
      await api.createPolicyVersion({
        doc_type: creatingFor, version: versionLabel.trim(), content, created_by: createdBy.trim(),
      })
      setCreatingFor(null)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl mb-1">Active Policy</h1>
      <p className="text-ink-muted text-sm mb-6">
        Every decision stores a snapshot reference to the exact version shown here at the moment it was made —
        not a live pointer. Publishing a new version supersedes the current one; nothing is ever edited in place.
      </p>

      <div className="max-w-sm mb-6">
        <label className="block">
          <span className="block text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Your name (for the audit trail)</span>
          <input
            type="text"
            value={createdBy}
            onChange={(e) => setCreatedBy(e.target.value)}
            placeholder="e.g. Jane Procurement Lead"
            className="w-full bg-paper border border-rule px-2 py-1.5 font-sans text-sm text-ink normal-case focus:border-ink outline-none"
          />
        </label>
      </div>

      {error && <p className="text-accent text-sm mb-4 font-mono">{error}</p>}

      {!current && <p className="text-ink-muted font-mono text-sm">Loading...</p>}

      <div className="grid gap-4">
        {current && Object.entries(DOC_LABELS).map(([docType, label]) => {
          const version = current[docType]
          if (!version) return null
          const isOpen = expanded === docType
          const isCreating = creatingFor === docType
          return (
            <div key={docType} className="border border-rule">
              <div className="flex items-center gap-3 p-4">
                <button
                  onClick={() => setExpanded(isOpen ? null : docType)}
                  className="flex-1 flex items-center justify-between text-left min-w-0"
                >
                  <div className="min-w-0">
                    <span className="font-serif text-lg mr-3">{label}</span>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">
                      v{version.version} &middot; effective {new Date(version.effective_at).toLocaleDateString()}
                    </span>
                  </div>
                  <span className="font-mono text-xs text-ink-muted ml-3 flex-shrink-0">{isOpen ? '−' : '+'}</span>
                </button>
                <button
                  onClick={() => startNewVersion(docType, version)}
                  className="font-mono text-[10px] uppercase tracking-wider border border-ink px-2.5 py-1.5 hover:bg-ink hover:text-paper transition-colors flex-shrink-0"
                >
                  + New version
                </button>
              </div>

              {isOpen && (
                <div className="border-t border-rule p-4 bg-paper-deep">
                  <pre className="whitespace-pre-wrap text-xs font-mono leading-relaxed max-h-96 overflow-y-auto">
                    {version.content}
                  </pre>
                </div>
              )}

              {isCreating && (
                <div className="border-t border-ink p-4">
                  <p className="font-mono text-xs uppercase tracking-wider text-ink-muted mb-3">
                    New version of {label} — pre-filled with the current content, edit before publishing
                  </p>
                  <label className="block mb-3">
                    <span className="block text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Version label</span>
                    <input
                      type="text"
                      value={versionLabel}
                      onChange={(e) => setVersionLabel(e.target.value)}
                      placeholder="e.g. 2026-08-17"
                      className="w-full max-w-xs bg-paper border border-rule px-2 py-1.5 font-mono text-sm text-ink focus:border-ink outline-none"
                    />
                  </label>
                  <label className="block mb-3">
                    <span className="block text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Content (markdown)</span>
                    <TextArea rows={16} value={content} onChange={(e) => setContent(e.target.value)} />
                  </label>
                  <div className="flex gap-3">
                    <button
                      onClick={publish}
                      disabled={submitting || !versionLabel.trim() || !content.trim() || !createdBy.trim()}
                      className="font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {submitting ? 'Publishing...' : 'Publish version'}
                    </button>
                    <button
                      onClick={() => setCreatingFor(null)}
                      className="font-mono text-xs uppercase tracking-wider text-ink-muted hover:text-ink px-4 py-2"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
