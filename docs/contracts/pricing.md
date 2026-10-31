# Shared calculator v0.1

Owner: Syed Arhan. Implemented on arhan/pricing-calculator from a8df082; not yet merged.
Policy basis: user's October 31 report that both developers approved financial-proposal.md.
No schema, dependencies, auth or public route changes. No database access or reservations.

## Python boundary for quotation and invoice consumers

Import Charge, Discount, PricingError and calculate_price from pricing.services.
Pass an iterable of immutable Charge values; calculate_price returns immutable PriceTotal
and ordered LineTotal values. INR is the supported currency. Callers supply Decimal
values, never floats. Money is exact to cents (trailing zeroes allowed), quantities are
positive integers (booleans rejected). Tax and percentage discount rates are finite
Decimal values from 0 through 100. Negative variant adjustments are allowed only when
the resulting unit price remains nonnegative. No global Decimal precision is assumed.

Charge fields: charge_id (unique stable string), quantity, unit_price,
variant_adjustment (default 0), tax_rate (default 0), optional product_id, optional
single Discount. A plan fee is an explicit separate Charge with quantity 1. Product
and variant prices come from Abbas's trusted catalog records, not posted totals.

Discount fields: rule_id (stable string), kind FIXED/PERCENTAGE, value, scope
SUBSCRIPTION/PRODUCT (default SUBSCRIPTION), optional product_id (required only for
PRODUCT). A product rule must match the charge's product_id. All occurrences of a
rule_id must have the same definition. A fixed rule's budget applies once across its
selected matching charges; two different rule IDs are independent budgets.

The service rejects malformed shapes, duplicate charge IDs, conflicting rule definitions,
invalid rates/amounts, mismatched product scope and unsupported currency via PricingError.
This is a ValueError subclass; feature forms should map it to validation errors. This
module does not define a new HTTP error shape or route.

LineTotal: charge_id, gross, discount, net, tax, total, discount_rule_id.
PriceTotal: currency, lines (tuple in input order), subtotal, discount, net, tax, total.
All monetary outputs are Decimal values with two decimal places. Future JSON consumers
must serialize them as decimal strings. An empty preview returns zero; invoice issuance
must separately require valid service lines.

## Calculation

Gross = quantity × (unit_price + variant_adjustment). Apply the chosen discount before tax.
Percentage discount rounds half-up per line and caps at gross. Fixed discounts cap at
eligible gross and allocate proportionally in cents using largest remainder, ties broken
lexicographically by stable charge_id. This is invariant to input ordering. Compute tax
on each net line, half-up to cents, then sum line results for aggregates.

Money arithmetic uses integer cents, and percentage arithmetic uses exact Fraction
ratios derived from Decimal. These standard-library types avoid floating-point and
caller-context rounding. No additional package is needed.

## Caller responsibilities and remaining integration

The caller selects one eligible discount per charge and supplies trusted effective
prices/rates. It must validate pricing date, discount dates/thresholds, usage availability,
customer ownership, plan minimum quantities and lifecycle state. These checks are not
implemented by a pure calculator accepting already selected rules. Preview must not
reserve usage. Billing must revalidate eligibility and atomically reserve usage, create
immutable snapshots and advance schedule state in its eventual transaction.

Abbas's quotation/subscription modules do not yet exist at this baseline. They should
call this service, not copy calculations into models/templates/JavaScript. The first
consumer integration and persistence/concurrency tests remain required. Existing catalog
effective_sales_price displays a single unit's base-plus-variant sum; it is not a quote
or invoice total. Calculator rejection of negative effective prices does not fix catalog
validation itself; the review document assigns that defect to Abbas.

Run: .venv/Scripts/python.exe manage.py test pricing --settings=config.test_settings.
Tests cover approved examples, boundaries, exact fractional rates, discount scope,
permutation stability, 300 allocation cases, malformed inputs and low Decimal precision.
Django SimpleTestCase disallows database queries, guarding preview purity.
