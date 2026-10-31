# Brightloop project handoff

## 1. Project snapshot

Brightloop is a subscription-management web app for the hackathon problem statement.
A1–A3 and B1 are merged on main; B2 pure calculator was committed on arhan/pricing-calculator (3ec3956)
and pushed to origin. Developer 2 has now implemented B2 Tax & Discount Configuration in the `billing` app
on branch `arhan/billing-config`. 111 automated tests pass against local PostgreSQL.

Current stack: Python 3.14.4, Django 5.2.18, PostgreSQL 17.11, server-rendered HTML. Exact dependencies are pinned in requirements.txt. Syed's B1 shared UI (`arhan/shared-ui`) was merged into `main`. Abbas's A1 platform, A2 public authentication, and A3 catalog & customer views are implemented.

## 2. Ownership and scope

Developer 1: Abbas Saeed — platform, authentication, catalog, plans, quotations, subscriptions.
Developer 2: Syed Arhan — shared UI, pricing/taxes/discounts, billing, invoices, payments, reporting.
See WORK_DIVISION.md for full responsibilities and cross-module change rules.

Current assistant assists Syed. Abbas previously merged B1 and implemented A2/A3.
Developer 2 implemented the approved pure calculator (pricing/services.py) and now the B2 Tax & Discount configuration models, forms, and views (billing/).

## 3. Repository map

Active checkout: C:\Users\LENOVO\Desktop\brightloop\shared. Abbas's prior path was
C:\Users\abbas\Desktop\brightloop; local data/credentials are never shared.

- AGENTS.md: entry point both agents should read.
- README.md: setup, run, checks, configuration, limits.
- FOUNDATION.md: candidate technology/identity baseline and proposed financial policies.
- WORK_DIVISION.md / DEVELOPMENT_GUIDE.md: ownership, milestones, scope, acceptance.
- AI_AGENT_ENGINEERING_STANDARDS.md / AI_AGENT_HANDOFF_POLICY.md: required working policies.
- must_have.md / nice_to_have.md: organizer guidance supplied by user.
- config/: settings, URL routing, WSGI/ASGI, test settings.
- accounts/: custom user, database constraints, password validator, role/query guards, admin forms, public signup/login/logout/reset, throttling, migration, tests.
- catalog/: products, priced variants, customer directory, server-side cost-price confidentiality, migration, forms, views, tests.
- pricing/: exact pure calculation service and 18 tests; immutable Charge/Discount/LineTotal/PriceTotal values.
- billing/: TaxRate and DiscountRule models, database check constraints, forms, admin and staff CRUD views, migrations, tests.
- core/: home, database readiness, test_ui.
- templates/:
  - base.html: responsive shell, role-aware navigation (Products, Customers, Tax Rates, Discounts, Admin), message notices.
  - core/home.html: workspace landing page.
  - accounts/: signup, login, password reset flow templates.
  - catalog/: product list, product detail, product form, variant form, customer list, customer detail.
  - billing/: tax rate list & form, discount rule list & form.
  - components/: form_fields.html, empty_state.html.
- core/static/brightloop/app.css: shared UI design system.
- scripts/local_postgres.py: isolated local database init/start/stop/status/check.
- requirements.in / requirements.txt / pyproject.toml / .python-version: dependency and check baseline.
- .github/workflows/checks.yml: GitHub CI workflow.
- docs/contracts/: platform.md (v0.3), shared-ui.md, financial-proposal.md, pricing.md.
- docs/handoffs/: abbas.md and arhan.md: scoped continuation notes.
- docs/reviews/a2-a3-review.md: reproduced auth/catalog findings for Abbas.

## 4. Current status

**Implemented and verified locally:**
- A1: Platform and persistence — custom UUID/email user model, case-insensitive uniqueness, roles (`ADMIN`, `STAFF`, `CUSTOMER`), DB constraints for privilege escalation prevention.
- B1: Shared UI — base layout, responsive CSS, components, accessible form rendering.
- A2: Public authentication — public signup (forces `CUSTOMER` role), throttled login (`accounts/throttle.py`), logout, password reset flow with email links, password validator.
- A3: Customers & Catalog — `Product` and `ProductVariant` models with decimal pricing, non-negative DB check constraints, unique variant names per product, support for variant adjustments (+560.00 example), forms and responsive views, customer directory for staff/admin, server-side cost-price confidentiality.
- B2 (Calculator): side-effect-free calculation service in `pricing/services.py` with 18 tests (including 300 allocation permutations).
- B2 (Tax & Discount Config): `TaxRate` and `DiscountRule` models with check constraints, `TaxRateForm` and `DiscountRuleForm` with validation, Staff/Admin CRUD views, templates, navigation links, and 29 unit tests in `billing/tests.py`.
- 111 tests pass in ~3.4s against local PostgreSQL.
- Ruff check and format pass, pip check passes, Django system check (`manage.py check`) passes with 0 issues.

**In progress:** Abbas's next A4 plans/quotations per his handoff; Syed's calculator and billing configuration are ready for integration once A4 lands.

**Unstarted:** Plans/templates/subscriptions (A4–A6); B3 recurring billing; B4 invoices; B5 payments; B6 reports.

## 5. Technical contracts and decisions

See FOUNDATION.md, docs/contracts/platform.md, docs/contracts/shared-ui.md, docs/contracts/financial-proposal.md, and docs/contracts/pricing.md.

- `is_staff` is Django admin access, not the business STAFF role. Public signup unconditionally assigns `role=CUSTOMER`.
- Product `cost_price` is confidential; views omit it for customers and anonymous users.
- Prices and money use Decimal with 2 decimal places and non-negative database constraints.
- Tax and discount configuration lives in `billing/`. Scope is either `SUBSCRIPTION` or `PRODUCT`.

## 6. Recent meaningful changes

- Pushed pure calculator and A2/A3 review to origin on `arhan/pricing-calculator` (commit 3ec3956).
- Created branch `arhan/billing-config`.
- Implemented `billing` app: `TaxRate` and `DiscountRule` models, migrations, forms, views, templates, admin registration.
- Added 29 tests in `billing/tests.py` and regression test in `core/test_ui.py`.
- Total test suite now: 111 tests passing against PostgreSQL.

## 7. Open issues and risks

- Review reproduced forwarded-header throttle bypass, duplicate-variant IntegrityError,
  and accepted negative effective variant pricing in Abbas's modules. Abbas owns fixes; see docs/reviews/a2-a3-review.md.
- Integration between B2 calculator and quotation templates requires Abbas's A4 models.

## 8. Next actions

1. Commit and push `arhan/billing-config`.
2. Await Abbas's A4 (Plans & Quotation Templates).
3. Connect B2 calculation service with quotation previews and subscription billing lines once A4 lands.
4. Implement B3 Recurring Billing (scheduler, due-period selection, unique period constraint).

## 9. Run and verification instructions

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py check
```

## 10. Handoff checkpoint

October 31, 2026. Branch: arhan/billing-config.
Final integrated suite: 111 tests passed with PostgreSQL. All checks green.
