import { useEffect, useState } from 'react'
import Badge from '../components/Badge.jsx'

import { api } from '../api/client.js'

export default function VendorsPage() {
  const [vendors, setVendors] = useState(null)

  useEffect(() => { api.listVendors().then(setVendors) }, [])

  return (
    <div>
      <h1 className="text-3xl mb-1">Approved Vendor Master</h1>
      <p className="text-ink-muted text-sm mb-6">Synthetic vendor data. All agent decisions ground vendor qualification checks against this table.</p>

      {!vendors && <p className="text-ink-muted font-mono text-sm">Loading...</p>}

      <div className="grid gap-3">
        {vendors && vendors.map((v) => {
          const certs = JSON.parse(v.certifications || '[]')
          return (
            <div key={v.vendor_id} className="border border-rule p-4 flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-serif text-lg">{v.name}</span>
                  <span className="font-mono text-[10px] text-ink-muted">{v.vendor_id}</span>
                  <Badge variant={v.approval_status === 'approved' ? 'approved' : 'rejected'}>
                    {v.approval_status}
                  </Badge>
                </div>
                <p className="text-xs text-ink-muted mb-2">{v.category}</p>
                <div className="flex flex-wrap gap-2">
                  {certs.map((c) => (
                    <span key={c.name} className="font-mono text-[10px] border border-rule px-1.5 py-0.5 text-ink-muted">
                      {c.name} &middot; exp {c.expiry_date}
                    </span>
                  ))}
                </div>
                {v.note && <p className="text-xs text-accent mt-2">{v.note}</p>}
              </div>
              <div className="text-right text-xs font-mono text-ink-muted flex-shrink-0">
                {v.on_time_pct != null && <div>On-time: {v.on_time_pct}%</div>}
                {v.defect_rate_pct != null && <div>Defect: {v.defect_rate_pct}%</div>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
