import { useEffect, useState } from 'react'
import Badge from '../components/Badge.jsx'
import { Field, TextInput, NumberInput, DateInput, Select, TextArea } from '../components/forms/Field.jsx'
import { CATEGORIES } from '../constants.js'
import { api } from '../api/client.js'

const emptyCert = () => ({ name: '', expiry_date: '' })

function AddVendorForm({ onCreated, onCancel }) {
  const [name, setName] = useState('')
  const [category, setCategory] = useState(CATEGORIES[0])
  const [approvalStatus, setApprovalStatus] = useState('approved')
  const [onTimePct, setOnTimePct] = useState('')
  const [defectRatePct, setDefectRatePct] = useState('')
  const [note, setNote] = useState('')
  const [certifications, setCertifications] = useState([emptyCert()])
  const [createdBy, setCreatedBy] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const updateCert = (i, field, value) =>
    setCertifications((cs) => cs.map((c, idx) => (idx === i ? { ...c, [field]: value } : c)))
  const addCert = () => setCertifications((cs) => [...cs, emptyCert()])
  const removeCert = (i) => setCertifications((cs) => cs.filter((_, idx) => idx !== i))

  const canSubmit = name.trim() && category && createdBy.trim()

  const submit = async () => {
    setError(null)
    setSubmitting(true)
    try {
      await api.createVendor({
        name: name.trim(),
        category,
        approval_status: approvalStatus,
        certifications: certifications
          .filter((c) => c.name.trim() && c.expiry_date)
          .map((c) => ({ name: c.name.trim(), expiry_date: c.expiry_date })),
        on_time_pct: onTimePct === '' ? null : Number(onTimePct),
        defect_rate_pct: defectRatePct === '' ? null : Number(defectRatePct),
        note: note.trim() || null,
        created_by: createdBy.trim(),
      })
      onCreated()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="border border-ink p-5 mb-6">
      <p className="font-mono text-xs uppercase tracking-wider text-ink-muted mb-4">Add vendor</p>
      <div className="grid sm:grid-cols-2 gap-4 mb-4">
        <Field label="Name">
          <TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Summit Freight Alliance" />
        </Field>
        <Field label="Category">
          <Select options={CATEGORIES} value={category} onChange={(e) => setCategory(e.target.value)} />
        </Field>
        <Field label="Approval status">
          <Select
            options={[{ value: 'approved', label: 'Approved' }, { value: 'not_approved', label: 'Not approved' }]}
            value={approvalStatus}
            onChange={(e) => setApprovalStatus(e.target.value)}
          />
        </Field>
        <Field label="Your name (for the audit trail)">
          <TextInput value={createdBy} onChange={(e) => setCreatedBy(e.target.value)} placeholder="e.g. Jane Procurement Lead" />
        </Field>
        <Field label="On-time delivery % (optional)">
          <NumberInput value={onTimePct} onChange={(e) => setOnTimePct(e.target.value)} min={0} max={100} step={0.1} />
        </Field>
        <Field label="Defect / return rate % (optional)">
          <NumberInput value={defectRatePct} onChange={(e) => setDefectRatePct(e.target.value)} min={0} max={100} step={0.1} />
        </Field>
      </div>

      <Field label="Note (optional)" hint="Anything a specialist should know — e.g. a monitoring flag or scope caveat.">
        <TextArea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
      </Field>

      <div className="mt-4">
        <p className="text-xs font-mono uppercase tracking-wide text-ink-muted mb-2">Certifications (optional)</p>
        <div className="grid gap-2">
          {certifications.map((c, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="flex-1">
                <TextInput
                  value={c.name}
                  onChange={(e) => updateCert(i, 'name', e.target.value)}
                  placeholder="e.g. ISO 9001:2015"
                />
              </div>
              <DateInput value={c.expiry_date} onChange={(e) => updateCert(i, 'expiry_date', e.target.value)} />
              <button onClick={() => removeCert(i)} className="text-accent font-mono text-xs px-1" title="Remove certification">×</button>
            </div>
          ))}
        </div>
        <button onClick={addCert} className="mt-2 font-mono text-xs uppercase tracking-wider text-ink-muted hover:text-ink">
          + Add certification
        </button>
      </div>

      {error && <p className="text-accent text-sm mt-4 font-mono">{error}</p>}

      <div className="flex gap-3 mt-5">
        <button
          onClick={submit}
          disabled={submitting || !canSubmit}
          className="font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? 'Adding...' : 'Add vendor'}
        </button>
        <button
          onClick={onCancel}
          className="font-mono text-xs uppercase tracking-wider text-ink-muted hover:text-ink px-4 py-2"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

export default function VendorsPage() {
  const [vendors, setVendors] = useState(null)
  const [adding, setAdding] = useState(false)

  const load = () => api.listVendors().then(setVendors)
  useEffect(() => { load() }, [])

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-1">
        <h1 className="text-3xl">Approved Vendor Master</h1>
        {!adding && (
          <button
            onClick={() => setAdding(true)}
            className="font-mono text-xs uppercase tracking-wider border border-ink px-3 py-1.5 hover:bg-ink hover:text-paper transition-colors flex-shrink-0"
          >
            + Add vendor
          </button>
        )}
      </div>
      <p className="text-ink-muted text-sm mb-6">All agent decisions ground vendor qualification checks against this table.</p>

      {adding && (
        <AddVendorForm
          onCreated={() => { setAdding(false); load() }}
          onCancel={() => setAdding(false)}
        />
      )}

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
