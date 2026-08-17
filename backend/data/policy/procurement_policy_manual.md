# Procurement Policy Manual

**Document ID:** POL-PROC-001
**Version:** 2026-06-01
**Status:** Active
**Owner:** Procurement Governance Office

*This document is synthetic content generated for the ProcureOps demo. It does not represent a real company's policy.*

## 1. Purpose and Scope

This manual governs all purchase requisitions, sourcing decisions, invoice processing, and inventory replenishment across the organization. It applies to every purchase regardless of funding source, and to every requester regardless of seniority. Exceptions require CFO sign-off under Section 8.

## 2. Procurement Categories

All spend is classified into one of six categories, each with its own Delegation of Authority (DOA) thresholds (see the DOA Matrix, document POL-DOA-001):

- IT Hardware & Software
- Office Supplies & Equipment
- Professional Services
- Raw Materials / Production Inputs
- Facilities & Maintenance
- Logistics & Freight

IT Hardware & Software carries the lowest per-tier thresholds of any category because of elevated data-security and asset-control risk — a $9,000 laptop refresh order requires the same approval tier as a $50,000 raw-materials order in a lower-risk category.

## 3. Delegation of Authority (DOA) — Summary

Every purchase requisition must be approved by the lowest role whose threshold covers the requisition's total value, for its category. The full threshold table lives in the DOA Matrix document. A requisition that names an approver below the required tier is non-compliant and must be escalated, not auto-corrected.

## 4. Vendor Qualification Requirements

A vendor may only receive a purchase order if all of the following hold at the time the PO is issued:

1. The vendor appears in the Approved Vendor Master with status `approved`.
2. Every certification required for the vendor's category is present and its `expiry_date` is on or after the PO issue date. A certification is not valid "as of last renewal" — it is valid only up to its recorded expiry date.
3. The vendor has no active compliance hold.

Sourcing or Invoice Verification agents must treat an expired certification exactly as if the certification were absent. A vendor with one expired certificate among several valid ones is still non-compliant.

## 5. Competitive Bidding Requirements

Any requisition with an estimated total value at or above $10,000 requires a minimum of three (3) competing vendor quotes before a sourcing recommendation may be proposed. Quotes must be compared on **total landed cost** — unit price plus applicable tax, freight, and duty — never on headline unit price alone. A recommendation that selects a higher-total-landed-cost vendor over a lower one requires an explicit, documented justification (e.g., lead time, quality history); silent deviation from lowest total landed cost is a policy violation.

## 6. Vendor Neutrality Requirement

Sourcing recommendations must apply the same evaluation criteria to every quote in a comparison set. Repeated, unexplained selection of the same vendor across multiple sourcing cases where a competitor offered a lower total landed cost is a governance concern and must be flagged for human review, not silently repeated.

## 7. Three-Way Match Requirement

No invoice may be approved for payment until it has been reconciled against both its Purchase Order and its Goods Receipt Note (a "three-way match"). Reconciliation tolerance is **2% on unit price and quantity**; discrepancies within this tolerance may be noted but do not require escalation. Discrepancies outside this tolerance must be classified by type before routing:

- **Quantity mismatch** — invoiced or received quantity differs from PO quantity beyond tolerance.
- **Price mismatch** — invoiced unit price differs from the PO's agreed unit price beyond tolerance.
- **Unauthorized vendor** — the invoice's vendor does not match the PO's vendor, or the invoicing vendor is not on the Approved Vendor Master.

Each discrepancy type routes to a different resolution path (see Section 9). Misclassifying a discrepancy type is treated as a control failure, not a minor error, because it sends the case down the wrong resolution path.

## 8. Exception and Override Process

Any deviation from this manual — a purchase below vendor qualification standards, an invoice paid outside three-way-match tolerance, a DOA threshold bypass — requires a written reason code and CFO or CEO sign-off. Exceptions are never self-approved by the agent or system that identified the need for one.

## 9. Compliance and Fraud Indicators

The following patterns must always be flagged for human review and never auto-resolved, regardless of dollar value:

- **Duplicate invoice** — the same PO number, vendor, and amount (or amount within 1%) appears on more than one invoice within a 60-day window.
- **Split-PO pattern** — multiple purchase orders from the same requester, to the same vendor, within a 14-day window, whose combined total would have required a higher DOA tier than any individual PO reached. This is treated as a potential attempt to evade approval thresholds regardless of stated intent.
- **Vendor master anomaly** — an invoice or PO referencing a vendor not present in the Approved Vendor Master, or referencing a vendor whose approval status is not `approved`.

## 10. Reorder and Inventory Policy

Inventory Management proposals (reorder point, reorder quantity) are recommendations only. No agent may generate or transmit an actual purchase order from an inventory proposal without passing through the standard requisition and DOA workflow. A reorder quantity that would exceed the SKU's trailing 90-day average consumption by more than 3x must include a stated rationale (e.g., known upcoexing demand spike, supplier minimum order quantity) or be flagged for review.

## 11. Reason Codes

Every governance decision — an approval, a rejection, an escalation, an override — must carry one of the following reason codes: `WITHIN_DOA_THRESHOLD`, `EXCEEDS_DOA_THRESHOLD`, `VENDOR_CERT_EXPIRED`, `VENDOR_NOT_APPROVED`, `QTY_MISMATCH`, `PRICE_MISMATCH`, `UNAUTHORIZED_VENDOR`, `DUPLICATE_INVOICE_SUSPECTED`, `SPLIT_PO_PATTERN`, `WITHIN_TOLERANCE`, `MANUAL_OVERRIDE`, `INSUFFICIENT_INFORMATION`.
