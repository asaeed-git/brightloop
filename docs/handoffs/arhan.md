# Syed Arhan: incoming work

## Current checkpoint: B3 Recurring Billing Engine & B4 Invoices

October 31, 2026. Branch `arhan/recurring-billing-invoices`, based on `main` (c86c243, after Abbas's A5).

Implemented B3 (Recurring Billing Engine) and B4 (Invoices):
- `billing/models.py`:
  - `Invoice`: unique `number` (`INV-YYYYMM-XXXX`), link to `customer` and optional `subscription`, status (`DRAFT`, `CONFIRMED`, `PAID`, `CANCELLED`), `period_start`, `period_end`, `issue_date`, `due_date`, financial snapshots (`subtotal`, `discount_total`, `net_total`, `tax_total`, `total`, `amount_paid`), `amount_due`, `is_overdue`.
  - **Database Anti-Duplication Constraint**: Unique constraint on `(subscription, period_start)` strictly prevents double-billing for the same period.
  - `InvoiceLine`: immutable snapshots storing `product`, `variant`, `description`, `quantity`, frozen `unit_price`, `gross`, allocated `discount`, `net`, `tax`, `total`, and `discount_rule`.
  - `BillingRunRecord`: audit log of recurring billing runs with target date, executed by, subscriptions checked, invoices created, total billed amount, success status, and log messages.
- `billing/services.py`:
  - `generate_invoice_for_subscription(subscription, target_date)`: authoritative, transactional invoice creation calling B2 `calculate_price()`, enforcing anti-duplication, and freezing snapshot line items.
  - `advance_subscription_period(subscription, target_date)`: advances period start, end, and next billing date, handling contract expiry auto-closure per approved financial policy.
  - `run_recurring_billing(target_date, executed_by)`: queries active, unpaused subscriptions with `next_billing_date <= target_date`, bills each in an isolated atomic transaction, advances schedule, and records execution metrics.
- `billing/views.py` & `billing/urls.py`:
  - Staff invoice list with status filtering and text search.
  - Staff invoice detail with frozen lines breakdown, status badges, and confirm/cancel actions.
  - Printable invoice layout (`invoice_print`) for customer download or physical printing.
  - Customer portal: "My Invoices" list and detail scoped strictly to `request.user` via `scope_to_customer`.
  - Staff recurring billing engine execution view with manual trigger form and historical audit table.
- `templates/billing/`:
  - `invoice_list.html`, `invoice_detail.html`, `invoice_print.html`, `customer_invoice_list.html`, `customer_invoice_detail.html`, `billing_run_list.html`.
- `templates/base.html`:
  - Role-aware sidebar links: Staff/Admin see `Invoices` and `Billing Runs`; Customers see `My Invoices`.
- `billing/tests.py`:
  - 36 tests in `billing` covering models, database constraints, anti-duplication uniqueness, pricing accuracy, recurring billing runner, schedule advance, expiry auto-closure, invoice views, and customer ownership scoping.
- Total test suite: **158 tests passing in ~6.2s against local PostgreSQL**.

Verification actually run:
- Applied `billing.0002_billingrunrecord_invoice_invoiceline_and_more` migration to local PostgreSQL.
- Full test suite: 158 tests passed with 0 failures, 0 errors.
- Ruff linter: 0 errors across 93 files checked.
- Ruff formatter: all 93 files formatted.
- Django system check: 0 issues.
- Static assets collected cleanly.

Next:
- Commit and push `arhan/recurring-billing-invoices`.
- Proceed to B5 (Payments & Balances): payment recording, payment method/note, idempotency key, partial vs. full settlement, balance tracking, and overpayment prevention.

## Previous checkpoint: B2 Tax and Discount Configuration (merged to main)

Implemented `billing` app for B2 tax and discount configuration: `TaxRate` and `DiscountRule` models, check constraints, forms, views, templates, and 29 unit tests.

## Previous checkpoint: B2 pure calculator and A2/A3 review (merged to main)

Implemented `pricing/services.py`: exact integer-cent and Fraction calculation service with 18 tests.

## Previous B1 checkpoint (merged to main)

Shared responsive UI shell, CSS design system, and accessible form components.
