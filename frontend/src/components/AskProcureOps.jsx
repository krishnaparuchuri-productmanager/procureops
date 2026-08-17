import { useState } from 'react'
import { api } from '../api/client.js'
import DecisionCard from './DecisionCard.jsx'

const EXAMPLE = "We got 5 replacement laptops in, but the invoice says $1,265 each and the PO says $1,180 — can someone check this?"

const TASK_TYPE_LABELS = {
  requisition: 'Requisition Intake',
  sourcing: 'Sourcing / Quote Comparison',
  invoice: 'Invoice Verification',
  inventory: 'Inventory Management',
}
const TASK_TYPE_MODEL = { requisition: 'Haiku', sourcing: 'Sonnet', invoice: 'Sonnet', inventory: 'Haiku' }

// STATE MACHINE: idle -> routing -> (routed | ambiguous) -> [requisition only] processing -> done
export default function AskProcureOps({ vendors, onHandoff }) {
  const [text, setText] = useState(EXAMPLE)
  const [stage, setStage] = useState('idle')
  const [routeResult, setRouteResult] = useState(null)
  const [decisionResult, setDecisionResult] = useState(null)
  const [error, setError] = useState(null)

  const ask = async () => {
    setError(null)
    setDecisionResult(null)
    setStage('routing')
    try {
      const route = await api.classify(text)
      setRouteResult(route)

      if (route.ambiguous || !route.task_type) {
        setStage('ambiguous')
        return
      }

      if (route.task_type === 'requisition') {
        setStage('processing')
        const res = await api.proposeRequisition({ raw_text: text })
        setDecisionResult(res)
        setStage('done')
      } else {
        setStage('routed')
        onHandoff(route.task_type, text)
      }
    } catch (e) {
      setError(e.message)
      setStage('idle')
    }
  }

  return (
    <div className="border border-rule-strong p-5 mb-10">
      <p className="font-mono text-xs uppercase tracking-wider text-accent mb-2">Ask ProcureOps</p>
      <p className="text-sm text-ink-muted mb-4 max-w-2xl">
        Describe what you need in plain language. The Router classifies it live and hands off to the
        right specialist — the same handoff that happens automatically when this data arrives from a
        real upstream system.
      </p>

      <div className="flex gap-2 max-w-2xl">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="flex-1 bg-paper border border-rule px-3 py-2 font-sans text-sm text-ink focus:border-ink outline-none"
          placeholder="e.g. Need 10 office chairs for the new hires, about $1,800 total"
        />
        <button
          onClick={ask}
          disabled={stage === 'routing' || stage === 'processing' || !text.trim()}
          className="font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40 flex-shrink-0"
        >
          Ask
        </button>
      </div>

      {error && <p className="text-accent text-sm mt-3 font-mono">{error}</p>}

      {stage === 'routing' && (
        <p className="mt-4 text-sm font-mono text-ink-muted animate-pulse">🧭 Router (Haiku) analyzing request...</p>
      )}

      {stage === 'ambiguous' && routeResult && (
        <div className="mt-4 text-sm">
          <p className="text-accent mb-1">🧭 Router couldn't confidently classify this.</p>
          <p className="text-ink-muted">{routeResult.rationale}</p>
          <p className="text-ink-muted mt-1">Pick a specialist tab below and fill in the form directly.</p>
        </div>
      )}

      {(stage === 'routed' || stage === 'processing' || stage === 'done') && routeResult && (
        <p className="mt-4 text-sm font-mono">
          🧭 Router (Haiku): classified as <span className="text-accent">{TASK_TYPE_LABELS[routeResult.task_type]}</span>
          {' '}→ handing off to <span className="text-accent">{TASK_TYPE_LABELS[routeResult.task_type]}</span>
          {' '}({TASK_TYPE_MODEL[routeResult.task_type]})
        </p>
      )}

      {stage === 'routed' && (
        <p className="mt-2 text-sm text-ink-muted">
          This request needs structured data the Router can't extract from free text alone — jump to the{' '}
          <strong>{TASK_TYPE_LABELS[routeResult.task_type]}</strong> tab below, already selected for you.
        </p>
      )}

      {stage === 'processing' && (
        <p className="mt-2 text-sm font-mono text-ink-muted animate-pulse">Running Requisition Intake — retrieving policy context and reasoning...</p>
      )}

      {stage === 'done' && decisionResult && (
        <div className="mt-5 pt-5 border-t border-rule">
          <DecisionCard
            decisionType="requisition_intake"
            proposal={decisionResult.assessment}
            sources={decisionResult.sources}
            agentId={decisionResult.agent_id}
            usage={decisionResult.usage}
            vendors={vendors}
          />
        </div>
      )}
    </div>
  )
}
