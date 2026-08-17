// In dev, Vite proxies '/api' to localhost:8000 (see vite.config.js), so the
// relative path works. In production there's no backend behind the Pages
// domain, so VITE_API_URL must point at the deployed Railway backend
// (e.g. https://procureops-backend-production.up.railway.app/api) — set as
// a build-time env var in the Cloudflare Pages project settings.
const BASE = import.meta.env.VITE_API_URL || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    const err = new Error(detail.detail || `Request failed: ${res.status}`)
    err.status = res.status
    throw err
  }
  return res.json()
}

export const api = {
  listDecisions: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/decisions${qs ? `?${qs}` : ''}`)
  },
  getDecision: (id) => request(`/decisions/${id}`),
  reviewDecision: (id, body) =>
    request(`/decisions/${id}/review`, { method: 'POST', body: JSON.stringify(body) }),
  checkDrift: (id) => request(`/decisions/${id}/drift`),

  proposeRequisition: (body) =>
    request('/decisions/requisition', { method: 'POST', body: JSON.stringify(body) }),
  proposeSourcing: (body) =>
    request('/decisions/sourcing', { method: 'POST', body: JSON.stringify(body) }),
  proposeSourcingStrategy: (body) =>
    request('/decisions/sourcing-strategy', { method: 'POST', body: JSON.stringify(body) }),
  proposeInvoice: (body) =>
    request('/decisions/invoice', { method: 'POST', body: JSON.stringify(body) }),
  proposeInventory: (body) =>
    request('/decisions/inventory', { method: 'POST', body: JSON.stringify(body) }),

  classify: (userInput) =>
    request('/route', { method: 'POST', body: JSON.stringify({ user_input: userInput }) }),

  listVendors: () => request('/vendors'),
  getAudit: (limit = 50) => request(`/audit?limit=${limit}`),
  getPolicyCurrent: () => request('/policy/current'),
  getPolicyVersions: (docType) => request(`/policy/versions/${docType}`),
  getTraces: (limit = 50) => request(`/traces?limit=${limit}`),
  getNotifications: () => request('/notifications'),
}
