import { AGENTS } from '../constants.js'

const MODEL_COLOR = { haiku: 'text-ink-muted', sonnet: 'text-accent' }

export default function AgentBadge({ agentId, usage }) {
  const agent = AGENTS[agentId]
  if (!agent) return <span className="font-mono text-xs text-ink-muted">{agentId}</span>

  return (
    <span className="inline-flex items-center gap-2 font-mono text-xs">
      <span className="text-ink">{agent.label}</span>
      <span className={`${MODEL_COLOR[agent.tier]} border border-rule px-1.5 py-0.5 text-[10px] uppercase tracking-wider`}>
        {agent.model}
      </span>
      {usage && (
        <span className="text-ink-muted text-[11px]">
          {usage.latency_ms != null && `${(usage.latency_ms / 1000).toFixed(1)}s`}
          {usage.input_tokens != null && ` · ${usage.input_tokens + (usage.output_tokens || 0)} tokens`}
        </span>
      )}
    </span>
  )
}
