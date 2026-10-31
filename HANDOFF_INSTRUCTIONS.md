# Brightloop project handoff

## 1. Project snapshot

Milestones A1–A4 (Platform, Public Authentication, Customers & Catalog, and Plans & Quotations) and Developer 2's B1 (Shared UI), B2 (Pure Pricing Calculator), and B2 (Tax & Discount Configuration in `billing`) are merged on `main` and locally verified. Brightloop is a subscription-management web app for the hackathon problem statement.

Current stack: Python 3.14.4, Django 5.2.18, PostgreSQL 17.11, server-rendered HTML. Exact dependencies are pinned in requirements.txt. Syed's B1 shared UI, B2 pricing calculator, and B2 billing config (`billing/`) were merged into `main`. Abbas's A1 platform, A2 public authentication, A3 catalog & customer views, and A4 plans & quotation templates are implemented.

## 2. Ownership and scope

Developer 1: Abbas Saeed — platform, authentication, catalog, plans, quotations, subscriptions.
Developer 2: Syed Arhan — shared UI, pricing/taxes/discounts, billing, invoices, payments, reporting.
See WORK_DIVISION.md for full responsibilities and cross-module change rules.

Current assistant merged Syed's B1, B2 pricing calculator, and B2 billing configuration into `main`, addressed code review findings, implemented Abbas's A4 plans and quotation templates scope, and verified integration across both developers' modules.

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
- pricing/: pure pricing calculation service, cents allocation with largest remainder, comprehensive test suite.
- billing/: TaxRate and DiscountRule models, database check constraints, forms, admin and staff CRUD views, migrations, tests.
- core/: home, database readiness, test_ui.
- templates/:
  - base.html: responsive shell, role-aware navigation (Plans, Products, Customers, Tax Rates, Discounts, Admin), message notices.
  - core/home.html: workspace landing page.
  - accounts/: signup, login, password reset flow templates.
  - catalog/: product list, product detail, product form, variant form, customer list, customer detail.
  - plans/: plan list, plan detail, plan form, template list, template detail, template form.
  - billing/: tax rate list & form, discount rule list & form.
  - components/: form_fields.html, empty_state.html.
- core/static/brightloop/app.css: shared UI design system.
- scripts/local_postgres.py: isolated local database init/start/stop/status/check.
- requirements.in / requirements.txt / pyproject.toml / .python-version: dependency and check baseline.
- .github/workflows/checks.yml: GitHub CI workflow.
- docs/contracts/: platform.md (v0.4), shared-ui.md, financial-proposal.md, pricing.md.
- docs/reviews/: a2-a3-review.md: reproduced auth/catalog findings addressed by Abbas.
- docs/handoffs/: abbas.md and arhan.md: scoped continuation notes.

## 4. Current status

**Implemented and verified locally:**
- Git on main branch; remote tracking origin/main at https://github.com/asaeed-git/brightloop.git.
- Merged Syed's `arhan/shared-ui`, `arhan/pricing-calculator`, and `arhan/billing-config` into `main`.
- A1: Platform and persistence — custom UUID/email user model, case-insensitive uniqueness, roles (`ADMIN`, `STAFF`, `CUSTOMER`), DB constraints for privilege escalation prevention.
- B1: Shared UI — base layout, responsive CSS, components, accessible form rendering.
- A2: Public authentication — public signup (forces `CUSTOMER` role), hardened throttled login (`accounts/throttle.py`), logout, password reset flow with email links, password validator (>=9 chars, uppercase, lowercase, special character, no digit required).
- A3: Customers & Catalog — `Product` and `ProductVariant` models with decimal pricing, non-negative DB check constraints, unique variant names per product, support for variant adjustments (+560.00 example), forms and responsive views, customer directory for staff/admin, server-side guarantee excluding confidential `cost_price` from customer view.
- B2: Pricing Calculator — side-effect free calculation service (`pricing.services.calculate_price`) allocating fixed discounts in integer cents using largest remainder, rounding percentage discounts and taxes per line half-up to cents.
- B2: Billing Configuration — `TaxRate` and `DiscountRule` models with check constraints, `TaxRateForm` and `DiscountRuleForm` with validation, Staff/Admin CRUD views, templates, navigation links in sidebar, and 29 unit tests in `billing/tests.py`.
- A4: Plans & Quotation Templates — `Plan` model with 4 billing intervals (`DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`), non-negative base plan price, minimum quantity validation, availability dates (`available_from` / `available_until`), and configurable lifecycle flags (`can_pause`, `can_early_close`, `auto_close_on_expiry`, `can_renew`). `QuotationTemplate` model with `validity_days` and `QuotationTemplateLine` items. Live pricing calculation preview powered by B2 service.
- All integrated tests pass against local PostgreSQL.
- Ruff check and format pass, pip check passes, Django system check (`manage.py check`) passes with 0 issues.

**In progress:** Next feature slice A5 (Subscription Lifecycle).

**Unstarted:** Subscriptions (A5), customer portal (A6), recurring billing worker (B3), invoices (B4), payments (B5), reporting (B6), scale/performance testing, deployment.

## 5. Technical contracts and decisions

See FOUNDATION.md, docs/contracts/platform.md, docs/contracts/shared-ui.md, docs/contracts/financial-proposal.md, and docs/contracts/pricing.md.

- `is_staff` is Django admin access, not the business STAFF role. Public signup unconditionally assigns `role=CUSTOMER`.
- Product `cost_price` is confidential; views omit it for customers and anonymous users.
- Prices and money use Decimal with 2 decimal places and non-negative database constraints.
- `Plan.price` is the recurring base plan fee per cycle.
- Product line quantities must meet or exceed `Plan.min_quantity`.
- Quotation templates bundle a plan and zero or more product/variant lines with default quantities and validity in days.
- Previews consume `pricing.services.calculate_price` without database mutations or side-effects.
- Tax and discount configuration lives in `billing/`. Scope is either `SUBSCRIPTION` or `PRODUCT`.

## 6. Recent meaningful changes

- Merged `arhan/billing-config` into `main`, bringing in `TaxRate` and `DiscountRule` models, forms, staff/admin views, navigation, and tests.
- Reconciled `config/settings.py`, `config/urls.py`, `templates/base.html`, `FOUNDATION.md`, and `HANDOFF_INSTRUCTIONS.md`.
- Hardened `accounts/throttle.py` to use `REMOTE_ADDR` directly, preventing client-spoofed `X-Forwarded-For` headers from bypassing rate limits.
- Fixed variant uniqueness validation in `catalog/forms.py` and `catalog/views.py` so duplicate variant names on the same product cleanly re-render with field errors instead of raising an unhandled `IntegrityError`.
- Enforced non-negative effective sales price validation on `Product` and `ProductVariant`.
- Created `plans` app with `Plan`, `QuotationTemplate`, and `QuotationTemplateLine` models, migrations, forms, views, and templates.
- Added live quote pricing calculation preview to template detail view using B2's `calculate_price`.

## 7. Open issues and risks

- Integrating quotation templates and billing configuration into the full subscription lifecycle (A5) and recurring billing worker (B3) is the next milestone.

## 8. Next actions

1. Push merged `main` to `origin/main`.
2. Begin A5 (Subscription Lifecycle):
   - Model `Subscription` with unique numbers, customer link, plan, start/expiry dates, payment terms, status (`DRAFT`, `QUOTATION`, `CONFIRMED`, `ACTIVE`, `CLOSED`).
   - Model `SubscriptionLine` with product, variant, quantity, agreed unit price.
   - Quotation creation from template.
   - Lifecycle transition state machine (draft -> quotation -> confirmed -> active -> closed) and action buttons.

## 9. Run and verification instructions

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py check
```

## 10. Handoff checkpoint

October 31, 2026. Branch: main. All tests passing against PostgreSQL. Clean working tree after merging `arhan/billing-config`.
