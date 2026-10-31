# Brightloop project handoff

## 1. Project snapshot

Milestones A1–A5 (Platform, Public Authentication, Customers & Catalog, Plans & Quotation Templates, and Subscription Lifecycle) and Developer 2's B1 (Shared UI), B2 (Pure Pricing Calculator), and B2 (Tax & Discount Configuration in `billing`) are implemented and locally verified. Brightloop is a subscription-management web app for the hackathon problem statement.

Current stack: Python 3.14.4, Django 5.2.18, PostgreSQL 17.11, server-rendered HTML. Exact dependencies are pinned in requirements.txt. Syed's B1 shared UI, B2 pricing calculator, and B2 billing config (`billing/`) were merged into `main`. Abbas's A1 platform, A2 public authentication, A3 catalog & customer views, A4 plans & quotation templates, and A5 subscription lifecycle are implemented. 151 automated tests pass against PostgreSQL in ~2.3s.

## 2. Ownership and scope

Developer 1: Abbas Saeed — platform, authentication, catalog, plans, quotations, subscriptions.
Developer 2: Syed Arhan — shared UI, pricing/taxes/discounts, billing, invoices, payments, reporting.
See WORK_DIVISION.md for full responsibilities and cross-module change rules.

Current assistant merged Syed's B1, B2 pricing calculator, and B2 billing configuration into `main`, addressed code review findings, implemented Abbas's A4 plans, and completed Abbas's A5 subscription lifecycle milestone.

## 3. Repository map

Root: C:\Users\abbas\Desktop\brightloop.

- AGENTS.md: entry point both agents should read.
- README.md: setup, run, checks, configuration, limits.
- FOUNDATION.md: candidate technology/identity baseline and approved financial policies.
- WORK_DIVISION.md / DEVELOPMENT_GUIDE.md: ownership, milestones, scope, acceptance.
- AI_AGENT_ENGINEERING_STANDARDS.md / AI_AGENT_HANDOFF_POLICY.md: required working policies.
- must_have.md / nice_to_have.md: organizer guidance supplied by user.
- config/: settings, URL routing, WSGI/ASGI, test settings.
- accounts/: custom user, database constraints, password validator, role/query guards, admin forms, public signup/login/logout/reset, hardened throttling, migration, tests.
- catalog/: products, priced variants, customer directory, server-side cost-price confidentiality, non-negative pricing validation, migration, forms, views, tests.
- plans/: plans (daily/weekly/monthly/yearly), quotation templates, template lines, pricing calculator integration, migration, forms, views, tests.
- subscriptions/: `Subscription` and `SubscriptionLine` models, database check constraints, lifecycle state machine (`DRAFT` → `QUOTATION` → `CONFIRMED` → `ACTIVE` → `CLOSED`), pause/resume, early close, renewal, quotation from template, live B2 pricing breakdown, views, forms, migrations, tests.
- pricing/: pure pricing calculation service, cents allocation with largest remainder, comprehensive test suite.
- billing/: TaxRate and DiscountRule models, database check constraints, forms, admin and staff CRUD views, migrations, tests.
- core/: home, database readiness, test_ui.
- templates/:
  - base.html: responsive shell, role-aware navigation (Plans, Products, Subscriptions, Customers, Tax Rates, Discounts, Admin), message notices.
  - core/home.html: workspace landing page.
  - accounts/: signup, login, password reset flow templates.
  - catalog/: product list, product detail, product form, variant form, customer list, customer detail.
  - plans/: plan list, plan detail, plan form, template list, template detail, template form.
  - subscriptions/: subscription list (with status tabs), subscription detail (with lines, pure B2 pricing breakdown, and lifecycle action controls), subscription form, subscription from template.
  - billing/: tax rate list & form, discount rule list & form.
  - components/: form_fields.html, empty_state.html.
- core/static/brightloop/app.css: shared UI design system.
- scripts/local_postgres.py: isolated local database init/start/stop/status/check.
- requirements.in / requirements.txt / pyproject.toml / .python-version: dependency and check baseline.
- .github/workflows/checks.yml: GitHub CI workflow.
- docs/contracts/: platform.md (v0.5), shared-ui.md, financial-proposal.md, pricing.md.
- docs/reviews/: a2-a3-review.md: reproduced auth/catalog findings addressed by Abbas.
- docs/handoffs/: abbas.md and arhan.md: scoped continuation notes.
- docs/handoffs/developer-sync-oct31.md: team sync report.

## 4. Current status

**Implemented and verified locally:**
- Git on main branch; remote tracking origin/main at https://github.com/asaeed-git/brightloop.git.
- Merged Syed's `arhan/shared-ui`, `arhan/pricing-calculator`, and `arhan/billing-config` into `main`.
- A1: Platform and persistence — custom UUID/email user model, case-insensitive uniqueness, roles (`ADMIN`, `STAFF`, `CUSTOMER`), DB constraints for privilege escalation prevention.
- B1: Shared UI — base layout, responsive CSS, components, accessible form rendering.
- A2: Public authentication — public signup (forces `CUSTOMER` role), hardened throttled login (`accounts/throttle.py`), logout, password reset flow with email links, password validator.
- A3: Customers & Catalog — `Product` and `ProductVariant` models with decimal pricing, non-negative DB check constraints, unique variant names per product, support for variant adjustments (+560.00 example), forms and responsive views, customer directory for staff/admin, server-side guarantee excluding confidential `cost_price` from customer view.
- B2: Pricing Calculator — side-effect free calculation service (`pricing.services.calculate_price`) allocating fixed discounts in integer cents using largest remainder, rounding percentage discounts and taxes per line half-up to cents.
- B2: Billing Configuration — `TaxRate` and `DiscountRule` models with check constraints, `TaxRateForm` and `DiscountRuleForm` with validation, Staff/Admin CRUD views, templates, navigation links in sidebar, and 29 unit tests in `billing/tests.py`.
- A4: Plans & Quotation Templates — `Plan` model with 4 billing intervals (`DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`), non-negative base plan price, minimum quantity validation, availability dates (`available_from` / `available_until`), and configurable lifecycle flags (`can_pause`, `can_early_close`, `auto_close_on_expiry`, `can_renew`). `QuotationTemplate` model with `validity_days` and `QuotationTemplateLine` items. Live pricing calculation preview powered by B2 service.
- A5: Subscription Lifecycle — `Subscription` and `SubscriptionLine` models with unique human-readable numbers (`SUB-YYYYMM-XXXX`), lifecycle state transitions (`DRAFT` → `QUOTATION` → `CONFIRMED` → `ACTIVE` → `CLOSED`), minimum quantity enforcement, quotation expiry validation, upfront billing period calculation with day clamping and contract clipping, pause/resume, early close restrictions, contract renewals, quotation creation from template, and live calculation preview using Syed's B2 calculation service.
- 151 tests pass in ~2.3s against local PostgreSQL.
- Ruff check and format pass, Django system check (`manage.py check`) passes with 0 issues.

**In progress:** Abbas's A6 (Customer Subscription Experience polish) / Syed's B3 (Recurring Billing).

**Unstarted:** Invoices (B4), payments (B5), reporting (B6), scale/performance testing, deployment.

## 5. Technical contracts and decisions

See FOUNDATION.md, docs/contracts/platform.md, docs/contracts/shared-ui.md, docs/contracts/financial-proposal.md, and docs/contracts/pricing.md.

- `is_staff` is Django admin access, not the business STAFF role. Public signup unconditionally assigns `role=CUSTOMER`.
- Product `cost_price` is confidential; views omit it for customers and anonymous users.
- Prices and money use Decimal with 2 decimal places and non-negative database constraints.
- `Plan.price` is the recurring base plan fee per cycle.
- Product line quantities must meet or exceed `Plan.min_quantity`.
- Quotation templates bundle a plan and zero or more product/variant lines with default quantities and validity in days.
- Previews consume `pricing.services.calculate_price` without database mutations or side-effects.
- `Subscription` satisfies all model fields agreed with Developer 2 in `developer-sync-oct31.md`: `customer`, `plan`, `status`, `start_date`, `expiry_date`, `current_period_start`, `current_period_end`, `next_billing_date`, `payment_terms_days`, `can_pause`, `is_paused`, `auto_close_on_expiry`, `can_renew`.
- Active billing selection contract for B3: select `Subscription.objects.filter(status='ACTIVE', is_paused=False, next_billing_date__lte=today)` for period `[current_period_start, current_period_end)`.

## 6. Recent meaningful changes

- Implemented `subscriptions` app (A5): `Subscription` and `SubscriptionLine` models, database constraints, lifecycle transitions, pause/resume, renewal, template conversion, pure B2 pricing preview, forms, views, templates, and admin registration.
- Added 18 unit and integration tests in `subscriptions/tests.py` and regression test in `core/test_ui.py`.
- Total test suite now: 151 tests passing against PostgreSQL 17.11.

## 7. Open issues and risks

- B3 Recurring Billing can now directly connect to the `Subscription` and `SubscriptionLine` models.

## 8. Next actions

1. Commit and push A5 changes to `origin/main`.
2. Await Syed's B3 recurring billing worker and B4 invoice snapshots.
3. Complete A6 (Customer Portal "My Subscriptions" experience polish and self-serve actions).

## 9. Run and verification instructions

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py check
```

## 10. Handoff checkpoint

October 31, 2026. Branch: main. All 151 tests passing against PostgreSQL. Clean working tree after completing A5.
