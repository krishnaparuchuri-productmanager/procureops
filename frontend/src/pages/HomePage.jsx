import { Link } from 'react-router-dom'
import { AGENTS } from '../constants.js'
import NotificationsPanel from '../components/NotificationsPanel.jsx'

const SPECIALIST_CARDS = [
  {
    tab: 'requisition', agentId: 'procureops-requisition-intake',
    title: 'Requisition Intake',
    desc: 'Parses a free-text purchase request, checks it against the DOA matrix and vendor qualification, and either clears it or escalates.',
    gate: 'Threshold-based — can auto-clear',
  },
  {
    tab: 'sourcing_strategy', agentId: 'procureops-sourcing-strategy',
    title: 'Sourcing Strategy',
    desc: 'Turns a vague spend question into a vendor shortlist and weighted evaluation criteria — before any quotes exist.',
    gate: 'Always human-gated',
  },
  {
    tab: 'sourcing', agentId: 'procureops-sourcing',
    title: 'Sourcing / Quote Comparison',
    desc: 'Compares competing vendor quotes on total landed cost, applies the same criteria to every vendor, and recommends — never selects.',
    gate: 'Always human-gated',
  },
  {
    tab: 'invoice', agentId: 'procureops-invoice-verification',
    title: 'Invoice Verification',
    desc: 'Reconciles a Purchase Order, Goods Receipt Note, and Invoice, classifying any discrepancy by type before it routes to resolution.',
    gate: 'Always human-gated',
  },
  {
    tab: 'inventory', agentId: 'procureops-inventory-management',
    title: 'Inventory Management',
    desc: 'Monitors stock levels and proposes reorder points and quantities. Never issues a PO directly — proposals only.',
    gate: 'Threshold-based — can auto-clear',
  },
  {
    tab: 'contract_renewal', agentId: 'procureops-contract-renewal',
    title: 'Contract Renewal',
    desc: 'Checks a proposed renewal against company-configured, code-evaluated thresholds — small tail-spend renewals clear on their own, everything else goes to a human.',
    gate: 'Bounded autonomy — can auto-clear',
  },
]

const SECONDARY_LINKS = [
  { to: '/decisions', label: 'Decision Queue', desc: 'Every proposal, pending and decided' },
  { to: '/activity', label: 'Agent Activity', desc: 'Every agent call — model, latency, tokens, sources' },
  { to: '/vendors', label: 'Vendors', desc: 'The Approved Vendor Master' },
  { to: '/policy', label: 'Policy', desc: 'Active Procurement Policy Manual + DOA Matrix' },
  { to: '/audit', label: 'Audit Log', desc: 'INSERT-only record of every governance event' },
  { to: '/autonomy-policy', label: 'Autonomy Config', desc: 'The thresholds that let a renewal auto-clear' },
]

export default function HomePage() {
  return (
    <div>
      <h1 className="text-4xl mb-3">ProcureOps</h1>
      <p className="text-ink-muted text-base mb-8 max-w-2xl">
        A Router classifies incoming procurement requests and hands off to six specialists. Every
        proposal that touches money leaving the company is human-gated by design — an agent can never
        approve its own recommendation.
      </p>

      <NotificationsPanel />

      <div className="flex items-center gap-4 mb-10">
        <Link
          to="/new"
          className="font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2.5 hover:bg-ink hover:text-paper transition-colors"
        >
          Ask ProcureOps &rarr;
        </Link>
        <span className="text-sm text-ink-muted">Describe what you need in plain language — the Router picks the specialist.</span>
      </div>

      <h2 className="text-xl mb-4">The six specialists</h2>
      <div className="grid sm:grid-cols-2 gap-3 mb-10">
        {SPECIALIST_CARDS.map((c) => {
          const agent = AGENTS[c.agentId]
          return (
            <Link
              key={c.tab}
              to={`/new?tab=${c.tab}`}
              className="border border-rule p-4 hover:border-ink transition-colors block"
            >
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="font-serif text-lg">{c.title}</span>
                <span className="font-mono text-[10px] uppercase tracking-wider border border-rule px-1.5 py-0.5 text-ink-muted flex-shrink-0">
                  {agent.model}
                </span>
              </div>
              <p className="text-sm text-ink-muted mb-2">{c.desc}</p>
              <p className="font-mono text-[10px] uppercase tracking-wider text-accent">{c.gate}</p>
            </Link>
          )
        })}
      </div>

      <h2 className="text-xl mb-4">Decision support — not a specialist</h2>
      <Link to="/negotiation" className="border border-rule p-4 hover:border-ink transition-colors block mb-10">
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="font-serif text-lg">Negotiation Brief</span>
          <span className="font-mono text-[10px] uppercase tracking-wider border border-rule px-1.5 py-0.5 text-ink-muted flex-shrink-0">Sonnet</span>
        </div>
        <p className="text-sm text-ink-muted">
          BATNA, a reasoned ZOPA estimate, and an integrative trade menu for whoever runs the actual
          negotiation. Not gated — there's no decision to approve, just a strategy brief.
        </p>
      </Link>

      <h2 className="text-xl mb-4">Browse</h2>
      <div className="grid sm:grid-cols-3 gap-3">
        {SECONDARY_LINKS.map((l) => (
          <Link key={l.to} to={l.to} className="border border-rule p-3 hover:border-ink transition-colors block">
            <p className="font-mono text-xs uppercase tracking-wider mb-1">{l.label}</p>
            <p className="text-xs text-ink-muted">{l.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
