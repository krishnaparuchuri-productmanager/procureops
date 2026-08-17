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
  if (decisionType === 'sourcing_strategy') {
    return (
      <div>
        <h3 className="text-2xl mb-1 capitalize">{proposal.sourcing_approach?.replace(/_/g, ' ')}</h3>
        <p className="text-sm text-ink-muted">
          {proposal.shortlist?.length || 0} vendor{proposal.shortlist?.length === 1 ? '' : 's'} shortlisted
          {proposal.competitive_bidding_required && ' · competitive bidding required'}
        </p>
      </div>
    )
  }
  if (decisionType === 'contract_renewal') {
    const passed = proposal.rule_check?.passed
    const increasePct = proposal.current_annual_value_usd
      ? ((proposal.proposed_annual_value_usd - proposal.current_annual_value_usd) / proposal.current_annual_value_usd) * 100
      : null
    return (
      <div>
        <h3 className="text-2xl mb-1">{passed ? 'Cleared automatically' : 'Requires human review'}</h3>
        <p className="text-sm text-ink-muted">
          {vendorLabel(proposal.vendor_id, vendors)} · ${Number(proposal.current_annual_value_usd).toLocaleString()}
          {' → '}${Number(proposal.proposed_annual_value_usd).toLocaleString()}
          {increasePct != null && ` (${increasePct >= 0 ? '+' : ''}${increasePct.toFixed(1)}%)`}
        </p>
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
  if (decisionType === 'contract_renewal') {
    const checks = proposal.rule_check?.checks || []
    const RESULT_STYLE = {
      passed: 'text-ink border-ink',
      failed: 'text-accent border-accent',
      not_applicable: 'text-ink-muted border-rule',
    }
    const RESULT_MARK = { passed: '✓', failed: '✗', not_applicable: '–' }
    return (
      <div>
        <div className="mb-4">
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-2">
            Bounded-autonomy rule check — {proposal.rule_check?.reason_code}
          </p>
          <div className="grid gap-1.5">
            {checks.map((c) => (
              <div key={c.name} className="flex items-start gap-2.5 text-sm">
                <span className={`flex-shrink-0 w-4 h-4 flex items-center justify-center font-mono text-[10px] border rounded-full mt-0.5 ${RESULT_STYLE[c.result]}`}>
                  {RESULT_MARK[c.result]}
                </span>
                <span className={c.result === 'failed' ? 'text-accent' : ''}>{c.detail}</span>
              </div>
            ))}
          </div>
        </div>
        {proposal.key_terms_assessment && (
          <div className="mb-3">
            <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Terms assessment</p>
            <p className="text-sm">{proposal.key_terms_assessment}</p>
          </div>
        )}
        {proposal.risk_notes && (
          <div className="mb-3">
            <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Risk notes</p>
            <p className="text-sm">{proposal.risk_notes}</p>
          </div>
        )}
        {proposal.recommended_negotiation_points?.length > 0 && (
          <div>
            <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Worth raising before signing</p>
            <ul className="text-sm list-disc list-inside space-y-0.5">
              {proposal.recommended_negotiation_points.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </div>
        )}
      </div>
    )
  }
  if (decisionType === 'sourcing_strategy') {
    return (
      <div>
        {proposal.shortlist?.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-2">Shortlist</p>
            <div className="grid gap-2">
              {proposal.shortlist.map((s) => (
                <div key={s.vendor_id} className="border border-rule p-2.5">
                  <p className="text-sm mb-1">{vendorLabel(s.vendor_id, vendors)}</p>
                  <p className="text-xs text-ink-muted mb-1">{s.rationale}</p>
                  {s.risk_flags?.map((f, i) => (
                    <p key={i} className="text-xs text-accent">⚠ {f}</p>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}
        {proposal.evaluation_criteria?.length > 0 && (
          <div className="mb-3">
            <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-2">Evaluation criteria</p>
            <div className="grid gap-1">
              {proposal.evaluation_criteria.map((c) => (
                <div key={c.criterion} className="flex items-center gap-3 text-sm">
                  <span className="font-mono text-xs text-ink-muted w-10 flex-shrink-0">{c.weight_pct}%</span>
                  <span>{c.criterion}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {proposal.approach_rationale && (
          <p className="text-sm text-ink-muted">{proposal.approach_rationale}</p>
        )}
      </div>
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
