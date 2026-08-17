import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { CATEGORIES } from '../constants.js'

/**
 * Threshold row — a single split-fill bar showing where a configured number
 * sits between "auto-clear zone" and "human decides zone," with a plain
 * number input driving it. Original layout for this project: one bar per
 * metric with a hard divider at the threshold, not a two-handle range
 * slider — deliberately, since every one of these four thresholds is a
 * single min OR max cutoff, never an actual two-sided range.
 */
function ThresholdRow({ label, description, value, onChange, unit, scaleMax, direction, step, min = 0 }) {
  const pct = Math.min(100, Math.max(0, (Number(value) / scaleMax) * 100))
  const autoStyle = direction === 'max' ? { left: 0, width: `${pct}%` } : { left: `${pct}%`, width: `${100 - pct}%` }
  const humanStyle = direction === 'max' ? { left: `${pct}%`, width: `${100 - pct}%` } : { left: 0, width: `${pct}%` }
  const leftCaption = direction === 'max' ? 'Auto-clear zone' : 'Human decides'
  const rightCaption = direction === 'max' ? 'Human decides' : 'Auto-clear zone'

  return (
    <div className="mb-5 last:mb-0">
      <div className="flex items-start justify-between gap-4 mb-2">
        <div>
          <p className="text-sm">{label}</p>
          <p className="text-xs text-ink-muted">{description}</p>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <input
            type="number"
            value={value}
            onChange={(e) => onChange(e.target.value === '' ? 0 : Number(e.target.value))}
            step={step}
            min={min}
            className="w-20 bg-paper border border-rule px-2 py-1 font-mono text-sm text-right text-ink focus:border-ink outline-none"
          />
          <span className="font-mono text-xs text-ink-muted w-6">{unit}</span>
        </div>
      </div>
      <div className="relative h-2 bg-rule/50">
        <div className="absolute inset-y-0 bg-ink/60" style={autoStyle} />
        <div className="absolute inset-y-0 bg-accent/45" style={humanStyle} />
        <div className="absolute top-0 bottom-0 w-px bg-ink" style={{ left: `${pct}%` }} />
      </div>
      <div className="flex justify-between mt-1 font-mono text-[9px] uppercase tracking-wider text-ink-muted">
        <span>{leftCaption}</span>
        <span>{rightCaption}</span>
      </div>
    </div>
  )
}

const DEFAULT_NEW_BAND = {
  max_renewal_value_usd: 10000, min_vendor_on_time_pct: 90,
  max_vendor_defect_rate_pct: 2, max_price_increase_pct: 5,
}

const METRICS = [
  {
    key: 'max_renewal_value_usd', label: 'Max renewal value', unit: 'USD', scaleMax: 50000, direction: 'max', step: 500,
    description: 'Above this dollar amount, always a human call regardless of how strong the vendor looks.',
  },
  {
    key: 'min_vendor_on_time_pct', label: 'Min on-time delivery', unit: '%', scaleMax: 100, direction: 'min', step: 0.5,
    description: "Below this, the vendor's own delivery record isn't strong enough to clear on its own.",
  },
  {
    key: 'max_vendor_defect_rate_pct', label: 'Max defect / return rate', unit: '%', scaleMax: 5, direction: 'max', step: 0.1,
    description: 'Above this, quality history rules out an automatic renewal.',
  },
  {
    key: 'max_price_increase_pct', label: 'Max price increase', unit: '%', scaleMax: 15, direction: 'max', step: 0.5,
    description: 'Above this year-over-year increase, always a human call — even from a strong vendor.',
  },
]

export default function AutonomyPolicyPage() {
  const [policies, setPolicies] = useState([])
  const [vendorCategories, setVendorCategories] = useState([])
  const [edits, setEdits] = useState({})
  const [updatedBy, setUpdatedBy] = useState('')
  const [savingCategory, setSavingCategory] = useState(null)
  const [savedCategory, setSavedCategory] = useState(null)
  const [error, setError] = useState(null)
  const [adding, setAdding] = useState(false)
  const [newCategory, setNewCategory] = useState('')
  const [newBand, setNewBand] = useState(DEFAULT_NEW_BAND)
  const [creating, setCreating] = useState(false)

  const load = () => {
    api.listAutonomyPolicy().then(setPolicies).catch((e) => setError(e.message))
    api.getVendorCategories().then(setVendorCategories).catch(() => {})
  }
  useEffect(() => { load() }, [])

  // The real source of truth agents/autonomy_rules.py matches against — a
  // band whose category has zero vendors here will never actually run.
  const vendorCountFor = (category) => vendorCategories.find((c) => c.category === category)?.vendor_count ?? 0
  const categorySuggestions = [...new Set([...vendorCategories.map((c) => c.category), ...CATEGORIES])].sort()

  const startAdding = () => {
    setNewCategory('')
    setNewBand(DEFAULT_NEW_BAND)
    setAdding(true)
  }

  const categoryTaken = policies.some((p) => p.category === newCategory.trim())

  const create = async () => {
    setError(null)
    setCreating(true)
    try {
      await api.createAutonomyPolicy({ category: newCategory.trim(), ...newBand, updated_by: updatedBy })
      setAdding(false)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  const valueFor = (p, key) => edits[p.category]?.[key] ?? p[key]

  const setValue = (category, key, value) => {
    setEdits((prev) => ({ ...prev, [category]: { ...prev[category], [key]: value } }))
    setSavedCategory(null)
  }

  const save = async (p) => {
    setError(null)
    setSavingCategory(p.category)
    try {
      await api.updateAutonomyPolicy(p.category, {
        max_renewal_value_usd: valueFor(p, 'max_renewal_value_usd'),
        min_vendor_on_time_pct: valueFor(p, 'min_vendor_on_time_pct'),
        max_vendor_defect_rate_pct: valueFor(p, 'max_vendor_defect_rate_pct'),
        max_price_increase_pct: valueFor(p, 'max_price_increase_pct'),
        updated_by: updatedBy,
      })
      setEdits((prev) => {
        const next = { ...prev }
        delete next[p.category]
        return next
      })
      setSavedCategory(p.category)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setSavingCategory(null)
    }
  }

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-1">
        <h1 className="text-3xl">Autonomy Config</h1>
        {!adding && (
          <button
            onClick={startAdding}
            className="font-mono text-xs uppercase tracking-wider border border-ink px-3 py-1.5 hover:bg-ink hover:text-paper transition-colors flex-shrink-0"
          >
            + Add category
          </button>
        )}
      </div>
      <p className="text-ink-muted text-sm mb-6 max-w-3xl">
        These bands are the only thing that lets a Contract Renewal clear itself — see that specialist
        under <span className="font-mono">Simulate Request</span>. Every renewal is checked against all
        four numbers below as plain code, never by agent judgment: inside every band, it clears on its
        own; outside even one, a human decides. There's no universally correct setting here — only what
        your organization is comfortable treating as routine tail spend.
      </p>

      <div className="max-w-sm mb-6">
        <label className="block">
          <span className="block text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Your name (for the audit trail)</span>
          <input
            type="text"
            value={updatedBy}
            onChange={(e) => setUpdatedBy(e.target.value)}
            placeholder="e.g. Jane Procurement Lead"
            className="w-full bg-paper border border-rule px-2 py-1.5 font-sans text-sm text-ink normal-case focus:border-ink outline-none"
          />
        </label>
      </div>

      {error && <p className="text-accent text-sm mb-4 font-mono">{error}</p>}

      {adding && (
        <section className="border border-ink p-5 mb-4">
          <div className="flex items-center justify-between mb-4">
            <input
              type="text"
              list="autonomy-category-suggestions"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              placeholder="Category name"
              className="bg-paper border border-rule px-2 py-1.5 font-serif text-lg text-ink focus:border-ink outline-none w-full max-w-sm"
            />
            <datalist id="autonomy-category-suggestions">
              {categorySuggestions.filter((c) => !policies.some((p) => p.category === c)).map((c) => <option key={c} value={c} />)}
            </datalist>
          </div>
          <p className={`text-xs mb-4 -mt-2 ${categoryTaken ? 'text-accent' : 'text-ink-muted'}`}>
            {categoryTaken
              ? `'${newCategory.trim()}' already has a band — edit it below instead.`
              : newCategory.trim()
                ? vendorCountFor(newCategory.trim()) > 0
                  ? `${vendorCountFor(newCategory.trim())} vendor(s) currently use '${newCategory.trim()}' — this band will apply to them.`
                  : `No vendors currently use '${newCategory.trim()}' — this band won't apply to anyone until one does.`
                : "Type the exact category string your vendors use — Contract Renewal matches on it exactly."}
          </p>

          {METRICS.map((m) => (
            <ThresholdRow
              key={m.key}
              label={m.label}
              description={m.description}
              value={newBand[m.key]}
              onChange={(v) => setNewBand((b) => ({ ...b, [m.key]: v }))}
              unit={m.unit}
              scaleMax={m.scaleMax}
              direction={m.direction}
              step={m.step}
            />
          ))}

          <div className="flex gap-3 mt-4 pt-3 border-t border-rule">
            <button
              onClick={create}
              disabled={creating || !newCategory.trim() || !updatedBy.trim() || categoryTaken}
              className="font-mono text-xs uppercase tracking-wider border border-ink px-3 py-1.5 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {creating ? 'Creating...' : 'Create band'}
            </button>
            <button
              onClick={() => setAdding(false)}
              className="font-mono text-xs uppercase tracking-wider text-ink-muted hover:text-ink px-3 py-1.5"
            >
              Cancel
            </button>
          </div>
        </section>
      )}

      {policies.map((p) => {
        const vendorCount = vendorCountFor(p.category)
        return (
        <section key={p.category} className="border border-rule p-5 mb-4">
          <div className="flex items-center justify-between mb-1">
            <h2 className="font-serif text-lg">{p.category}</h2>
            {savedCategory === p.category && (
              <span className="font-mono text-[10px] uppercase tracking-wider text-ink-soft">Saved</span>
            )}
          </div>
          <p className={`text-xs mb-4 ${vendorCount === 0 ? 'text-accent' : 'text-ink-muted'}`}>
            {vendorCount === 0
              ? "No vendors currently use this category — this band won't apply to anyone."
              : `${vendorCount} vendor${vendorCount === 1 ? '' : 's'} currently use this category.`}
          </p>

          {METRICS.map((m) => (
            <ThresholdRow
              key={m.key}
              label={m.label}
              description={m.description}
              value={valueFor(p, m.key)}
              onChange={(v) => setValue(p.category, m.key, v)}
              unit={m.unit}
              scaleMax={m.scaleMax}
              direction={m.direction}
              step={m.step}
            />
          ))}

          <div className="flex items-center justify-between mt-4 pt-3 border-t border-rule">
            <p className="text-xs text-ink-muted">
              Last updated by {p.updated_by} &middot; {new Date(p.updated_at).toLocaleDateString()}
            </p>
            <button
              onClick={() => save(p)}
              disabled={!edits[p.category] || savingCategory === p.category || !updatedBy.trim()}
              className="font-mono text-xs uppercase tracking-wider border border-ink px-3 py-1.5 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {savingCategory === p.category ? 'Saving...' : 'Save band'}
            </button>
          </div>
        </section>
        )
      })}
    </div>
  )
}
