# Syed Arhan: incoming work

## Current checkpoint: B5 Payments & Balances

October 31, 2026. Branch `arhan/payments-balances`, based on `main` (commit `e58d07d`, after Abbas's A6).

Implemented Milestone B5 (Payments & Balances):
- `payments/models.py`:
  - `Payment`: UUID primary key, positive exact INR Decimal `amount` (`MinValueValidator(Decimal("0.01"))`), unique `idempotency_key` (max 128 chars), method choices (`CARD`, `UPI`, `BANK_TRANSFER`, `CASH`, `SIMULATED`), `paid_at` timestamp, `transaction_ref`, `notes`, FK to `billing.Invoice` (`on_delete=PROTECT`), and FK to `settings.AUTH_USER_MODEL` (`on_delete=PROTECT`).
  - Database check constraint `payments_payment_amount_positive` (`amount > 0.00`).
  - Indexes on `invoice` and `(customer, -paid_at)`.
- `payments/services.py`:
  - `record_payment(...)`:
    - Wraps payment recording in an atomic transaction (`transaction.atomic()`).
    - Row-level lock on `Invoice.objects.select_for_update()`.
    - **Idempotency & replay protection**: Replaying same `idempotency_key` with identical payload returns existing `Payment` without duplicate debit; mismatched payload with same key raises `PaymentConflictError`.
    - **Overpayment protection**: Rejects payments exceeding `invoice.amount_due` at the service level (`OverpaymentError`) and respects the database check constraint `billing_invoice_amount_paid_lte_total`.
    - **Partial settlement**: Updates `invoice.amount_paid`, keeps status `CONFIRMED`.
    - **Full settlement**: When `invoice.amount_paid >= invoice.total`, transitions `status` to `PAID` and sets `paid_at`.
- `payments/forms.py`:
  - `PaymentForm` for staff payment recording with method, amount, reference, notes, and optional UUID idempotency key.
- `payments/views.py` & `payments/urls.py`:
  - `payment_list`: Filterable staff directory of all recorded payments by method or search query (`invoice__number`, `customer__email`, `transaction_ref`), with total collected aggregation.
  - `payment_create`: Staff action to record partial or full settlement against any invoice with row locking and error handling.
  - `customer_payment_create`: Customer self-service payment recording/simulation, strictly scoped via `scope_to_customer` (cannot pay other customers' invoices; raises 404).
- `billing/views.py` & templates:
  - Added `OVERDUE` filter to staff invoice list (`billing/invoice_list.html`).
  - Added customer account balance summary (total invoiced, total settled, outstanding balance) in `billing/customer_invoice_list.html`.
  - Embedded payment history and "Record Payment" form in `billing/invoice_detail.html` (staff).
  - Embedded payment history and "Pay Statement / Simulate Payment" in `billing/customer_invoice_detail.html` (customer).
- `templates/base.html`:
  - Added role-aware `Payments` navigation link for Admin/Staff.
- `payments/tests.py`:
  - 16 tests covering partial settlement, full settlement, cumulative payments, overpayment rejection, unpayable invoice validation, idempotent replay, payload conflict rejection, DB positive amount constraint, concurrent payment race prevention with `select_for_update` (`PaymentConcurrencyTests`), staff view access, customer 403 on staff list, customer self-service simulation, customer cross-account payment isolation (HTTP 404), overdue filtering, and customer balance aggregation.
- Total test suite: **184 tests passing in ~8.1s against local PostgreSQL (127.0.0.1:55432)** with 0 failures and 0 errors.

Verification actually run:
- Applied `payments.0001_initial` migration to local PostgreSQL.
- Ran full test suite: 184 tests passed (184 OK, 0 failures).
- Ruff check: All checks passed across entire codebase (104 files).
- Ruff format check: 104 files formatted cleanly.
- Django system check: 0 issues.
- Migrations check: No uncreated migrations (`manage.py makemigrations --check --dry-run`).
- Static assets collected cleanly.

Next:
- Commit and push `arhan/payments-balances`.
- Milestone B6: Reports & scale testing (Developer 2).

## Previous checkpoint: B3 Recurring Billing Engine & B4 Invoices (merged to main)

Implemented B3 (Recurring Billing Engine) and B4 (Invoices):
- `billing/models.py`: `Invoice`, `InvoiceLine`, `BillingRunRecord` models with anti-duplication unique constraint on `(subscription, period_start)`.
- `billing/services.py`: `generate_invoice_for_subscription`, `advance_subscription_period`, `run_recurring_billing`.
- Views, templates, and 36 billing tests.

## Previous checkpoint: B2 Tax and Discount Configuration (merged to main)

Implemented `billing` app for B2 tax and discount configuration: `TaxRate` and `DiscountRule` models, check constraints, forms, views, templates, and 29 unit tests.

## Previous checkpoint: B2 pure calculator and A2/A3 review (merged to main)

Implemented `pricing/services.py`: exact integer-cent and Fraction calculation service with 18 tests.

## Previous B1 checkpoint (merged to main)

Shared responsive UI shell, CSS design system, and accessible form components.
