import { ConfidenceBadge } from './Badge.jsx'
import AgentBadge from './AgentBadge.jsx'
import SourceCitations from './SourceCitations.jsx'

const ACTION_LABELS = {
  auto_clear: 'Auto-cleared', escalate: 'Escalated', flag_missing_field: 'Missing information',
  approve: 'Approved', no_action: 'No action needed', propose_reorder: 'Reorder proposed',
  flag_before_reorder: 'Vendor issue flagged', flag_reorder_quantity: 'Quantity flagged',
  flag_ambiguous_data: 'Data quality flagged',
}

function vendorLabel(vendorId, vendors) {
  const v = vendors?.find((v) => v.vendor_id === vendorId)
  return v ? `${vendorId} — ${v.name}` : vendorId
}

function Headline({ decisionType, proposal, vendors }) {
  if (decisionType === 'requisition_intake') {
    return (
      <div>
        <h3 className="text-2xl mb-1">{ACTION_LABELS[proposal.action] || proposal.action}</h3>
        <p className="text-sm text-ink-muted">{proposal.doa_citation}</p>
      </div>
    )
  }
  if (decisionType === 'vendor_selection') {
    return (
      <div>
        <h3 className="text-2xl mb-1">
          {proposal.recommended_vendor_id
            ? `Recommends ${vendorLabel(proposal.recommended_vendor_id, vendors)}`
            : 'No vendor recommended'}
        </h3>
        {proposal.doa_escalation_needed && (
          <p className="text-sm text-accent">Requires {proposal.doa_tier} approval — exceeds the standard threshold.</p>
        )}
      </div>
    )
  }
  if (decisionType === 'invoice_verdict') {
    const label = proposal.discrepancy_type === 'none' ? 'Clean match' : proposal.discrepancy_type?.replace(/_/g, ' ')
    return (
      <div>
        <h3 className="text-2xl mb-1 capitalize">{label}</h3>
        <p className="text-sm text-ink-muted">
          {ACTION_LABELS[proposal.action] || proposal.action}
          {proposal.variance_pct != null && ` · ${proposal.variance_pct}% variance`}
          {proposal.duplicate_invoice_suspected && ' · Duplicate suspected'}
        </p>
      </div>
    )
  }
  if (decisionType === 'reorder_action') {
    return (
      <div>
        <h3 className="text-2xl mb-1">{ACTION_LABELS[proposal.action] || proposal.action}</h3>
        {proposal.proposed_reorder_qty != null && (
          <p className="text-sm text-ink-muted">Proposed quantity: {proposal.proposed_reorder_qty}</p>
        )}
      </div>
    )
  }
  return <h3 className="text-2xl mb-1">{decisionType}</h3>
}

function SpecialistDetail({ decisionType, proposal, vendors }) {
  if (decisionType === 'vendor_selection' && proposal.landed_costs?.length) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-rule text-left font-mono text-[10px] uppercase tracking-wide text-ink-muted">
              <th className="py-1.5 pr-3">Vendor</th>
              <th className="py-1.5 pr-3">Total Landed Cost</th>
              <th className="py-1.5">Status</th>
            </tr>
          </thead>
          <tbody>
            {proposal.landed_costs.map((lc) => (
              <tr key={lc.vendor_id} className="border-b border-rule last:border-0">
                <td className="py-1.5 pr-3">{vendorLabel(lc.vendor_id, vendors)}</td>
                <td className="py-1.5 pr-3 font-mono">${Number(lc.total_landed_cost).toLocaleString()}</td>
                <td className="py-1.5">
                  {lc.excluded ? (
                    <span className="text-accent text-xs">Excluded — {lc.exclusion_reason}</span>
                  ) : lc.vendor_id === proposal.recommended_vendor_id ? (
                    <span className="text-ink-soft text-xs font-mono uppercase tracking-wide">Recommended</span>
                  ) : (
                    <span className="text-ink-muted text-xs">Qualified</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {proposal.vendor_neutrality_note && (
          <p className="text-sm text-ink-muted mt-3">{proposal.vendor_neutrality_note}</p>
        )}
        {proposal.competitive_bidding_gap && (
          <p className="text-sm text-accent mt-2">Fewer than 3 quotes were supplied for a requisition at or above the competitive-bidding threshold.</p>
        )}
      </div>
    )
  }
  if (decisionType === 'invoice_verdict' && proposal.resolution_next_steps) {
    return (
      <div>
        <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Next steps</p>
        <p className="text-sm">{proposal.resolution_next_steps}</p>
      </div>
    )
  }
  if (decisionType === 'requisition_intake') {
    return (
      <dl className="grid grid-cols-2 gap-y-1 text-sm">
        <dt className="text-ink-muted">Category</dt><dd>{proposal.category || '—'}</dd>
        <dt className="text-ink-muted">Amount</dt><dd>{proposal.estimated_total_usd != null ? `$${Number(proposal.estimated_total_usd).toLocaleString()}` : '—'}</dd>
        <dt className="text-ink-muted">Vendor</dt><dd>{proposal.vendor_id ? vendorLabel(proposal.vendor_id, vendors) : '—'}</dd>
        <dt className="text-ink-muted">Cost center</dt><dd>{proposal.cost_center || '—'}</dd>
      </dl>
    )
  }
  return null
}

export default function DecisionCard({ decisionType, proposal, sources, agentId, usage, vendors, reasonCode }) {
  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-4">
        <Headline decisionType={decisionType} proposal={proposal} vendors={vendors} />
        <ConfidenceBadge confidence={proposal.confidence} />
      </div>

      <SpecialistDetail decisionType={decisionType} proposal={proposal} vendors={vendors} />

      {proposal.rationale && (
        <div className="mt-4">
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Reasoning</p>
          <p className="text-sm leading-relaxed">{proposal.rationale}</p>
        </div>
      )}

      {reasonCode && (
        <p className="mt-3 font-mono text-[10px] uppercase tracking-wider text-ink-muted">Reason code: {reasonCode}</p>
      )}

      {(agentId || usage) && (
        <div className="mt-4 pt-3 border-t border-rule">
          <AgentBadge agentId={agentId} usage={usage} />
        </div>
      )}

      {sources && (
        <div className="mt-5 pt-4 border-t border-rule">
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-2">Grounded in</p>
          <SourceCitations sources={sources} />
        </div>
      )}
    </div>
  )
}
