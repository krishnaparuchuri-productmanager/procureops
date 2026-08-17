/**
 * Horizontal stage tracker for a named procurement workflow. Original layout
 * for this project — numbered marks on a rule line, current stage filled in
 * accent, future stages outlined. Not modeled on any specific vendor's UI.
 */
export default function WorkflowStepper({ steps, currentIndex }) {
  return (
    <div className="flex items-start mb-6" aria-label="Workflow stage">
      {steps.map((label, i) => {
        const state = i < currentIndex ? 'done' : i === currentIndex ? 'current' : 'upcoming'
        return (
          <div key={label} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center flex-shrink-0">
              <div
                className={[
                  'w-6 h-6 flex items-center justify-center font-mono text-[10px] border rounded-full',
                  state === 'current' ? 'bg-accent border-accent text-paper' : '',
                  state === 'done' ? 'border-ink text-ink' : '',
                  state === 'upcoming' ? 'border-rule text-ink-muted' : '',
                ].join(' ')}
              >
                {state === 'done' ? '✓' : i + 1}
              </div>
              <span
                className={[
                  'mt-1.5 font-mono text-[9px] uppercase tracking-wider text-center whitespace-nowrap',
                  state === 'current' ? 'text-accent' : 'text-ink-muted',
                ].join(' ')}
              >
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={`flex-1 h-px mx-2 mb-4 ${state === 'done' ? 'bg-ink' : 'bg-rule'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
