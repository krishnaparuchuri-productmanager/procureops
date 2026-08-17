import { NavLink, Link } from 'react-router-dom'

const NAV_LINKS = [
  { to: '/decisions', label: 'Decisions' },
  { to: '/new', label: 'Simulate Request' },
  { to: '/negotiation', label: 'Negotiation Brief' },
  { to: '/autonomy-policy', label: 'Autonomy Config' },
  { to: '/activity', label: 'Agent Activity' },
  { to: '/vendors', label: 'Vendors' },
  { to: '/policy', label: 'Policy' },
  { to: '/audit', label: 'Audit Log' },
]

export default function NavBar() {
  return (
    <header className="sticky top-0 z-50 bg-paper/95 backdrop-blur border-b border-rule-strong">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-3 min-w-0">
            <span className="flex-shrink-0 w-7 h-7 border border-ink flex items-center justify-center font-mono text-[10px] font-medium">
              PO
            </span>
            <span className="font-serif text-lg leading-tight truncate">ProcureOps</span>
            <span className="hidden sm:inline font-mono text-[10px] uppercase tracking-wider text-ink-muted border border-rule px-1.5 py-0.5">
              Synthetic data
            </span>
          </Link>

          <nav className="flex items-center gap-1 font-mono text-xs uppercase tracking-wide" aria-label="Main navigation">
            {NAV_LINKS.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  [
                    'px-3 py-2 transition-colors duration-150 border-b-2',
                    isActive
                      ? 'text-accent border-accent'
                      : 'text-ink-muted border-transparent hover:text-ink hover:border-rule',
                  ].join(' ')
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
    </header>
  )
}
