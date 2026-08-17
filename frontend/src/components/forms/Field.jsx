export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="block text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">{label}</span>
      {children}
      {hint && <span className="block text-xs text-ink-muted mt-1 normal-case">{hint}</span>}
    </label>
  )
}

const inputClass = 'w-full bg-paper border border-rule px-2 py-1.5 font-sans text-sm text-ink focus:border-ink outline-none'

export function TextInput(props) {
  return <input type="text" className={inputClass} {...props} />
}

export function NumberInput(props) {
  return <input type="number" className={inputClass} {...props} />
}

export function DateInput(props) {
  return <input type="date" className={inputClass} {...props} />
}

export function TextArea(props) {
  return <textarea className={inputClass} {...props} />
}

export function Select({ options, ...props }) {
  return (
    <select className={inputClass} {...props}>
      {options.map((o) => (
        <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
      ))}
    </select>
  )
}
