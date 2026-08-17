import AgentBadge from './AgentBadge.jsx'
import { ConfidenceBadge } from './Badge.jsx'
import SourceCitations from './SourceCitations.jsx'

const PRIORITY_COLOR = { High: 'text-accent', Medium: 'text-ink-soft', Low: 'text-ink-muted' }

export default function NegotiationBriefCard({ brief, sources, agentId, usage }) {
  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-5">
        <h3 className="text-2xl">Negotiation Brief</h3>
        <ConfidenceBadge confidence={brief.confidence} />
      </div>

      <div className="grid sm:grid-cols-2 gap-5 mb-5">
        <div>
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">BATNA</p>
          <p className="text-sm leading-relaxed">{brief.batna}</p>
        </div>
        <div>
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">
            Reservation price
          </p>
          <p className="text-sm">
            {brief.reservation_price_usd != null ? `$${Number(brief.reservation_price_usd).toLocaleString()}` : 'No basis for one in the supplied context'}
          </p>
        </div>
      </div>

      <div className="mb-5">
        <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">ZOPA estimate</p>
        <p className="text-sm leading-relaxed text-ink-muted">{brief.zopa_estimate}</p>
      </div>

      {brief.trade_menu?.length > 0 && (
        <div className="mb-5">
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-2">
            Trade menu — integrative ("win-win") issues
          </p>
          <div className="grid gap-2">
            {brief.trade_menu.map((t, i) => (
              <div key={i} className="border border-rule p-3">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-sm">{t.issue}</span>
                  <span className="font-mono text-[10px] uppercase tracking-wider flex-shrink-0">
                    Our priority: <span className={PRIORITY_COLOR[t.our_priority]}>{t.our_priority}</span>
                    {' · Their priority: '}<span className={PRIORITY_COLOR[t.their_likely_priority]}>{t.their_likely_priority}</span>
                  </span>
                </div>
                <p className="text-xs text-ink-muted">{t.trade_idea}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {brief.leverage_factors?.length > 0 && (
        <div className="mb-5">
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-2">Leverage factors</p>
          <ul className="text-sm list-disc pl-4 space-y-1">
            {brief.leverage_factors.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}

      {brief.target_kpis?.length > 0 && (
        <div className="mb-5">
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-2">
            Target KPIs to carry into the room
          </p>
          <div className="grid gap-1 max-w-lg">
            {brief.target_kpis.map((k, i) => (
              <div key={i} className="flex items-baseline gap-3 text-sm">
                <span className="text-ink-muted flex-shrink-0 w-1/2">{k.kpi}</span>
                <span>{k.target}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {brief.risk_notes && (
        <div className="mb-5">
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Risk notes</p>
          <p className="text-sm text-accent">{brief.risk_notes}</p>
        </div>
      )}

      {brief.rationale && (
        <div className="mb-4">
          <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-1">Reasoning</p>
          <p className="text-sm leading-relaxed">{brief.rationale}</p>
        </div>
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
