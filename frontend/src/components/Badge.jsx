const VARIANTS = {
  pending: 'text-accent border-accent',
  approved: 'text-ink-soft border-ink-soft',
  rejected: 'text-accent border-accent bg-accent/10',
  auto: 'text-ink-muted border-rule',
  neutral: 'text-ink-muted border-rule',
}

export default function Badge({ children, variant = 'neutral' }) {
  return (
    <span
      className={`inline-block font-mono text-[10px] uppercase tracking-wider px-1.5 py-0.5 border ${VARIANTS[variant] || VARIANTS.neutral}`}
    >
      {children}
    </span>
  )
}

export function decisionStatusBadge(decision) {
  if (decision.auto_cleared) return <Badge variant="auto">Auto-cleared</Badge>
  if (decision.decision === 'approved') return <Badge variant="approved">Approved</Badge>
  if (decision.decision === 'rejected') return <Badge variant="rejected">Rejected</Badge>
  return <Badge variant="pending">Pending review</Badge>
}

const CONFIDENCE_VARIANTS = { High: 'approved', Medium: 'auto', Low: 'rejected' }

export function ConfidenceBadge({ confidence }) {
  if (!confidence) return null
  return <Badge variant={CONFIDENCE_VARIANTS[confidence] || 'neutral'}>{confidence} confidence</Badge>
}
