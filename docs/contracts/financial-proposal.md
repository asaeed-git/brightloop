# Financial contract proposal v0.1

Owner/proposer: Syed Arhan. Policy approved as written: on October 31, 2026, the user
explicitly reported that both developers approved this document, including discount
allocation and final-period charging. This is a record of that report, not a fabricated
direct approval message from Abbas. The proposal text below is retained as the approved
policy rationale. Its pure arithmetic boundary is now implemented in pricing/services.py;
see pricing.md. Proposed database operations and API/schema work are not implemented.
Consumers: Abbas's quotation/subscription services and Syed's billing/payment/reporting.

## Proposed calculator boundary

One pure server-side calculation service receives currency, effective pricing date,
plan fee, stable charge IDs, product/variant IDs, positive integer quantities, Decimal
unit prices/adjustments, applicable tax rate and one explicitly selected eligible
discount per charge. Trusted services load eligibility inputs; client totals are never
authoritative. Previews reserve no usage; billing revalidates current eligibility in
its transaction. Do not invent quote/customer endpoints to consume this draft.

Return each charge's gross, allocated discount, taxable net, tax and total plus matching
invoice aggregates. Use Decimal with INR/two-decimal display and JSON decimal strings
if jointly accepted. Reject floats, nonfinite amounts, negative net prices, nonpositive
or fractional quantities, percentages outside 0–100, duplicate charge IDs, ambiguous
discount selection and mixed currency. Explicit errors must map to agreed form/API errors.

## Proposed allocation and rounding for review

1. Charge gross = quantity × (base product price + variant adjustment); plan fee is
   a separate charge. Minimum quantity semantics remain Abbas's agreed plan rule.
2. Eligibility thresholds use the eligible pre-discount, pre-tax amount. No stacking.
   Define exact inclusive dates and scope IDs together before persistence code.
3. Percentage discounts: calculate and ROUND_HALF_UP each eligible charge discount to
   0.01, cap at gross. This is a per-line rule, not a rounded invoice percentage.
4. A subscription-scoped fixed discount is one invoice-wide amount, capped at eligible
   gross. Allocate proportionally across eligible gross charges in integer cents:
   floor each share, then distribute remaining cents by largest fractional remainder,
   breaking ties by stable charge ID. Product-scoped fixed discounts use the same
   allocation within matching product charges. Confirm fixed-discount scope with Abbas.
5. Tax each charge's discounted net using ROUND_HALF_UP to 0.01. Sum rounded line
   amounts for totals; never reround independent aggregates into a different result.
   This proposes one tax rate per charge; confirm whether multiple tax rules are needed.

Worked examples (documentation, not executed tests):

- Plan 100.00 + two units at 50.00 = 200.00. 10% discount on every charge gives
  20.00 discount, net 180.00, 5% tax 9.00, total 189.00. Pay 60.00 → due 129.00;
  pay 129.00 → due 0.00. Confirmed remains the partial-payment state.
- Three equal 1.00 charges with IDs A/B/C and fixed discount 1.00 allocate
  0.34/0.33/0.33. Net 0.66/0.67/0.67 sums to 2.00; at 5% tax, each line tax is
  0.03, so invoice total is 2.09. Line rounding is intentionally visible.
- A 0.10 charge at 5% tax produces 0.01 tax under half-up rounding.

## Proposed final-period policy and lifecycle boundaries

To make candidate upfront/no-proration semantics explicit: a final period starting
before expiry is charged at the full normal period price, but service end is clipped
to expiry. Example: monthly anchor Jan 31, expiry Feb 10 → bill Jan 31 once for service
[Jan 31, Feb 10), at full monthly price. This needs explicit human acceptance and clear
quotation disclosure; an alternative is to require expiry at billing boundaries.
Do not implement either until both developers settle this choice.

Abbas supplies billable effective lines, dates, status and pause/renewal/closure effects.
Agree one locking order for subscription lifecycle changes and billing, unique period
key, next-due writer, catch-up boundaries, and cancellation/replacement period retention.
Atomic invoice creation reserves discount use once per invoice/rule, stores snapshots,
and advances scheduling only on success. Email uses Abbas's outbox after commit.

Payments require positive exact amounts, invoice-level locking, a unique idempotency
key, same-key/same-payload replay and different-payload conflict behavior, no overpayment,
and an agreed correction policy. Reports separate invoiced net sales, collected cash,
outstanding and overdue, with explicit date/filter bases. Active count consumes Abbas's
definition. These are requirements for forthcoming contracts, not new endpoints.

## Integration gate

Both developers review examples, currency/precision, discount validity/selection/scope,
final-period billing, cancellation/reversal and lifecycle locking. Record actual
agreement in FOUNDATION.md and final domain contracts with the shared commit. Abbas
coordinates schemas, migration order and any dependency changes. Then implement the
calculator plus preview consumer and tests, before invoice/payment integration.
Required tests include rounding/threshold boundaries, allocation invariants, preview
purity, concurrent last-use reservation, duplicate period/payment requests, lifecycle
races, rollback, month-end/leap-year catch-up, ownership denial and report reconciliation.
No schema/dependency migration or rollback is needed for this proposal-only change.
