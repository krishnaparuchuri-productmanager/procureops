import { useState } from 'react'
import { Field, TextInput, NumberInput, DateInput, Select } from './Field.jsx'

const initial = {
  poId: 'PO-5003', poVendorId: 'V-001', sku: 'LAPTOP-ENT-11', poQty: 10, poUnitPrice: 1180.0, poDate: '2026-06-08',
  grnId: 'GRN-5003', grnQtyReceived: 10, grnDate: '2026-06-15',
  invoiceId: 'INV-5003', invoiceVendorId: 'V-001', invQty: 10, invUnitPrice: 1265.0, tax: 885.5, freight: 0, invoiceDate: '2026-06-17',
}

export default function InvoiceForm({ vendors, onSubmit, submitting }) {
  const [f, setF] = useState(initial)
  const set = (key) => (e) => setF((s) => ({ ...s, [key]: e.target.value }))

  const vendorOptions = [{ value: '', label: 'Select vendor...' }, ...vendors.map((v) => ({ value: v.vendor_id, label: `${v.vendor_id} — ${v.name}` }))]

  const total = Number(f.invQty || 0) * Number(f.invUnitPrice || 0) + Number(f.tax || 0) + Number(f.freight || 0)

  const canSubmit = f.poId && f.poVendorId && f.grnId && f.invoiceId && f.invoiceVendorId

  const submit = () => {
    onSubmit({
      match_id: `TWM-${Date.now()}`,
      po: {
        po_id: f.poId, vendor_id: f.poVendorId,
        line_items: [{ sku: f.sku, qty: Number(f.poQty), unit_price: Number(f.poUnitPrice) }],
        issue_date: f.poDate,
      },
      grn: {
        grn_id: f.grnId, po_id: f.poId,
        line_items: [{ sku: f.sku, qty_received: Number(f.grnQtyReceived) }],
        received_date: f.grnDate,
      },
      invoice: {
        invoice_id: f.invoiceId, po_id: f.poId, vendor_id: f.invoiceVendorId,
        line_items: [{ sku: f.sku, qty: Number(f.invQty), unit_price: Number(f.invUnitPrice) }],
        tax: Number(f.tax || 0), freight: Number(f.freight || 0), total,
        invoice_date: f.invoiceDate,
      },
    })
  }

  return (
    <div>
      <p className="text-sm text-ink-muted mb-5">
        In production, the Purchase Order and Goods Receipt Note come from the ERP, and the Invoice
        arrives from the vendor via an AP system or email — the agent reconciles all three the same
        way it would reconcile the fields below. Vendor mismatches between sections are intentional to
        test with.
      </p>

      <div className="grid md:grid-cols-3 gap-6">
        <fieldset className="border border-rule p-4">
          <legend className="font-mono text-xs uppercase tracking-wide text-ink-muted px-1">Purchase Order</legend>
          <div className="grid gap-3">
            <Field label="PO ID"><TextInput value={f.poId} onChange={set('poId')} /></Field>
            <Field label="Vendor"><Select options={vendorOptions} value={f.poVendorId} onChange={set('poVendorId')} /></Field>
            <Field label="SKU"><TextInput value={f.sku} onChange={set('sku')} /></Field>
            <Field label="Qty ordered"><NumberInput value={f.poQty} onChange={set('poQty')} /></Field>
            <Field label="Agreed unit price"><NumberInput value={f.poUnitPrice} onChange={set('poUnitPrice')} /></Field>
            <Field label="Issue date"><DateInput value={f.poDate} onChange={set('poDate')} /></Field>
          </div>
        </fieldset>

        <fieldset className="border border-rule p-4">
          <legend className="font-mono text-xs uppercase tracking-wide text-ink-muted px-1">Goods Receipt Note</legend>
          <div className="grid gap-3">
            <Field label="GRN ID"><TextInput value={f.grnId} onChange={set('grnId')} /></Field>
            <Field label="Qty received"><NumberInput value={f.grnQtyReceived} onChange={set('grnQtyReceived')} /></Field>
            <Field label="Received date"><DateInput value={f.grnDate} onChange={set('grnDate')} /></Field>
          </div>
        </fieldset>

        <fieldset className="border border-rule p-4">
          <legend className="font-mono text-xs uppercase tracking-wide text-ink-muted px-1">Invoice</legend>
          <div className="grid gap-3">
            <Field label="Invoice ID"><TextInput value={f.invoiceId} onChange={set('invoiceId')} /></Field>
            <Field label="Invoicing vendor" hint="Can differ from the PO vendor — that's an unauthorized-vendor test case.">
              <Select options={vendorOptions} value={f.invoiceVendorId} onChange={set('invoiceVendorId')} />
            </Field>
            <Field label="Qty invoiced"><NumberInput value={f.invQty} onChange={set('invQty')} /></Field>
            <Field label="Invoiced unit price"><NumberInput value={f.invUnitPrice} onChange={set('invUnitPrice')} /></Field>
            <Field label="Tax"><NumberInput value={f.tax} onChange={set('tax')} /></Field>
            <Field label="Freight"><NumberInput value={f.freight} onChange={set('freight')} /></Field>
            <Field label="Invoice date"><DateInput value={f.invoiceDate} onChange={set('invoiceDate')} /></Field>
            <div className="text-xs font-mono text-ink-muted">Total: ${total.toFixed(2)}</div>
          </div>
        </fieldset>
      </div>

      <button
        onClick={submit}
        disabled={submitting || !canSubmit}
        className="mt-5 font-mono text-xs uppercase tracking-wider border border-ink px-4 py-2 hover:bg-ink hover:text-paper transition-colors disabled:opacity-40"
      >
        {submitting ? 'Running agent...' : 'Submit for three-way match'}
      </button>
    </div>
  )
}
