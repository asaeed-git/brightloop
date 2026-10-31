# Brightloop project handoff

## 1. Project snapshot

Brightloop is a subscription-management web app for the hackathon problem statement.
Milestones A1–A6 (Abbas) and B1–B5 (Syed) are implemented and verified.
184 automated tests pass against local PostgreSQL in ~8.1s.

Current stack: Python 3.14.4, Django 5.2.18, PostgreSQL 17.11, server-rendered HTML. Exact dependencies are pinned in requirements.txt.

## 2. Ownership and scope

Developer 1: Abbas Saeed — platform, authentication, catalog, plans, quotations, subscription lifecycle, customer subscription experience (A1–A6).
Developer 2: Syed Arhan — shared UI, pricing/taxes/discounts, billing, invoices, payments, reporting (B1–B6).
See WORK_DIVISION.md for full responsibilities and cross-module change rules.

## 3. Repository map

Active checkout: C:\Users\LENOVO\Desktop\brightloop\shared.

- config/: settings, URL routing, WSGI/ASGI, test settings.
- accounts/: custom user, database constraints, password validator, role/query guards, admin forms, public signup/login/logout/reset, profile view and editing, throttling, tests.
- catalog/: products, priced variants, customer directory, server-side cost-price confidentiality, tests.
- plans/: 4 billing intervals, availability dates, lifecycle policies, quotation templates and lines, pricing previews.
- subscriptions/: subscription lifecycle (DRAFT → QUOTATION → CONFIRMED → ACTIVE → CLOSED), lines, pause/resume, early close, renewal, quotation conversion, seat quantity update with min seat enforcement, customer self-service actions, linked invoice display, pricing calculation integration.
- pricing/: exact pure calculation service and 18 tests; immutable Charge/Discount/LineTotal/PriceTotal values.
- billing/: TaxRate, DiscountRule, Invoice, InvoiceLine, and BillingRunRecord models, anti-duplication unique constraints, recurring billing runner, admin and staff views, customer "My Invoices" portal, tests.
- payments/: Payment model, positive amount constraint, idempotency key tracking, select_for_update row-locking settlement service, partial/full payment, overpayment protection, staff payment management, customer self-service simulation, tests.
- core/: home, database readiness, test_ui.
- templates/:
  - base.html: responsive shell, role-aware navigation (Plans, Products, Subscriptions, Invoices, Payments, Billing Runs, Customers, Tax Rates, Discounts, My Invoices, Account, Admin).
  - core/home.html: workspace landing page with role-specific dashboards.
  - accounts/: signup, login, password reset flow templates, profile.html.
  - catalog/: product list, product detail, product form, variant form, customer list, customer detail.
  - plans/: plan list, plan detail, plan form, template list, template detail, template form.
  - subscriptions/: subscription list, subscription detail with customer action buttons, subscription form, subscription from template.
  - billing/: tax rate list & form, discount rule list & form, invoice list with overdue filter, invoice detail with payment history & recording form, invoice print layout, customer invoice list with balance summary, customer invoice detail with payment simulation, billing run list.
  - payments/: payment_list.html with filterable method and search.
  - components/: form_fields.html, empty_state.html.
- core/static/brightloop/app.css: shared UI design system.
- scripts/local_postgres.py: isolated local database helper.
- docs/contracts/: platform.md, shared-ui.md, financial-proposal.md, pricing.md.
- docs/handoffs/: abbas.md, arhan.md, developer-sync-oct31.md.
- docs/reviews/a2-a3-review.md: reproduced auth/catalog findings for Abbas.

## 4. Current status

**Implemented and verified locally:**
- A1: Platform and persistence.
- B1: Shared UI — responsive shell, CSS design system, accessible form components.
- A2: Public authentication — signup, hardened throttle, logout, password reset flow.
- A3: Customers & Catalog — products with priced variants (+560), cost-price confidentiality.
- B2: Pricing & Billing Configuration — pure calculator (`pricing.services.calculate_price`) and `billing.TaxRate` / `billing.DiscountRule` configuration.
- A4: Plans & Quotations — 4 billing intervals, availability dates, quotation templates with live pricing preview.
- A5: Subscription Lifecycle — canonical lifecycle states, upfront periods, pause/resume, renewals, template conversion.
- B3: Recurring Billing Engine — due-period selection (`next_billing_date <= today`), atomic transactional processing, schedule advance, expiry auto-closure, and audit logging.
- B4: Invoices — immutable snapshot models, anti-duplication database constraint `(subscription, period_start)`, staff management, print view, and customer "My Invoices" portal.
- A6: Customer Subscription Experience — `/accounts/profile/` profile management, self-serve quote confirmation, pause/resume, early cancellation enforcement, seat quantity updates enforcing plan minimums, linked invoices in subscription detail.
- B5: Payments & Balances — `Payment` model with idempotency key, row-level locking (`select_for_update`), partial vs. full settlement, overpayment rejection, staff payment management, customer simulation, balance summary tracking.
- 184 tests pass in ~8.1s against local PostgreSQL.
- Ruff check and format pass across 104 files, Django system check passes with 0 issues.

**In progress / Next:** B6 Reports & scale testing (Developer 2).

## 5. Technical contracts and decisions

- Payment Settlement: Transactional with `Invoice.objects.select_for_update()`.
- Idempotency: Same key + matching payload returns existing payment; same key + mismatch raises `PaymentConflictError`.
- Balance Tracking: `amount_paid` tracked on `Invoice`; payments transition to `PAID` when fully settled.
- Anti-duplication: Database unique constraint on `Invoice(subscription, period_start)` guarantees zero duplicate billing.
- Immutable snapshots: `InvoiceLine` stores frozen unit price, gross, discount, net, tax, and total.
- Recurring worker advances `current_period_start`, `current_period_end`, and `next_billing_date` atomically upon successful invoice creation.
- Subscriptions with `expiry_date` reached auto-close if `auto_close_on_expiry=True`, or stop future scheduling.
- Customer self-serve actions strictly scoped to `request.user` via `scope_to_customer` and object ownership checks.

## 6. Run and verification instructions

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py check
```

## 7. Handoff checkpoint

October 31, 2026. Branch: `arhan/payments-balances`.
184 tests passing against PostgreSQL 17.11. All checks clean.
