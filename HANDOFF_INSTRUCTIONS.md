# Brightloop project handoff

## 1. Project snapshot

Brightloop is a subscription-management web app for the hackathon problem statement.
A1–A5, B1, and B2 are merged on `main`. Developer 2 has implemented Milestone B3 (Recurring Billing Engine)
and B4 (Invoices) on branch `arhan/recurring-billing-invoices`.
158 automated tests pass against local PostgreSQL in ~6.2s.

Current stack: Python 3.14.4, Django 5.2.18, PostgreSQL 17.11, server-rendered HTML. Exact dependencies are pinned in requirements.txt.

## 2. Ownership and scope

Developer 1: Abbas Saeed — platform, authentication, catalog, plans, quotations, subscription lifecycle (A1–A6).
Developer 2: Syed Arhan — shared UI, pricing/taxes/discounts, billing, invoices, payments, reporting (B1–B6).
See WORK_DIVISION.md for full responsibilities and cross-module change rules.

## 3. Repository map

Active checkout: C:\Users\LENOVO\Desktop\brightloop\shared.

- config/: settings, URL routing, WSGI/ASGI, test settings.
- accounts/: custom user, database constraints, password validator, role/query guards, admin forms, public signup/login/logout/reset, throttling, tests.
- catalog/: products, priced variants, customer directory, server-side cost-price confidentiality, tests.
- plans/: 4 billing intervals, availability dates, lifecycle policies, quotation templates and lines, pricing previews.
- subscriptions/: subscription lifecycle (DRAFT → QUOTATION → CONFIRMED → ACTIVE → CLOSED), lines, pause/resume, early close, renewal, quotation conversion, pricing calculation integration.
- pricing/: exact pure calculation service and 18 tests; immutable Charge/Discount/LineTotal/PriceTotal values.
- billing/: TaxRate, DiscountRule, Invoice, InvoiceLine, and BillingRunRecord models, anti-duplication unique constraints, recurring billing runner, admin and staff views, customer "My Invoices" portal, tests.
- core/: home, database readiness, test_ui.
- templates/:
  - base.html: responsive shell, role-aware navigation (Plans, Products, Subscriptions, Invoices, Billing Runs, Customers, Tax Rates, Discounts, My Invoices, Admin).
  - core/home.html: workspace landing page.
  - accounts/: signup, login, password reset flow templates.
  - catalog/: product list, product detail, product form, variant form, customer list, customer detail.
  - plans/: plan list, plan detail, plan form, template list, template detail, template form.
  - subscriptions/: subscription list, subscription detail, subscription form, subscription from template.
  - billing/: tax rate list & form, discount rule list & form, invoice list, invoice detail, invoice print layout, customer invoice list, customer invoice detail, billing run list.
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
- 158 tests pass in ~6.2s against local PostgreSQL.
- Ruff check and format pass across 93 files, Django system check passes with 0 issues.

**In progress:** B5 Payments & Balances.

**Unstarted:** B6 Reports & scale testing.

## 5. Technical contracts and decisions

- Anti-duplication: Database unique constraint on `Invoice(subscription, period_start)` guarantees zero duplicate billing.
- Immutable snapshots: `InvoiceLine` stores frozen unit price, gross, discount, net, tax, and total.
- Recurring worker advances `current_period_start`, `current_period_end`, and `next_billing_date` atomically upon successful invoice creation.
- Subscriptions with `expiry_date` reached auto-close if `auto_close_on_expiry=True`, or stop future scheduling.

## 6. Run and verification instructions

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py check
```

## 7. Handoff checkpoint

October 31, 2026. Branch: `arhan/recurring-billing-invoices`.
158 tests passing against PostgreSQL 17.11. All checks clean.
