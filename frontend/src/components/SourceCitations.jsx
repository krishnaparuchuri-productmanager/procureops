import { useState } from 'react'
import { CORPUS_LABELS } from '../constants.js'

function Citation({ chunk }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-rule">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-3 p-2.5 text-left"
      >
        <span className="text-sm truncate">
          <span className="font-mono text-[10px] uppercase tracking-wider text-ink-muted mr-2">
            {CORPUS_LABELS[chunk.corpus] || chunk.corpus}
          </span>
          {chunk.section_title}
        </span>
        <span className="font-mono text-xs text-ink-muted flex-shrink-0">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="border-t border-rule p-3 bg-paper-deep">
          <p className="text-[11px] font-mono text-ink-muted mb-2">{chunk.source_file}</p>
          <pre className="text-xs whitespace-pre-wrap font-sans leading-relaxed">{chunk.text}</pre>
        </div>
      )}
    </div>
  )
}

export default function SourceCitations({ sources }) {
  if (!sources || sources.length === 0) {
    return <p className="text-sm text-ink-muted">No sources were retrieved for this decision.</p>
  }
  return (
    <div>
      <p className="text-xs text-ink-muted mb-3 normal-case">
        The agent retrieved these {sources.length} section{sources.length === 1 ? '' : 's'} before reasoning —
        its rationale is grounded in this text, not general knowledge. Click any one to read the exact source.
      </p>
      <div className="grid gap-1.5">
        {sources.map((c) => (
          <Citation key={c.chunk_id} chunk={c} />
        ))}
      </div>
    </div>
  )
}
