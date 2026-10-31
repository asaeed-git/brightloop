# Brightloop project handoff

## 1. Project snapshot

Milestone M0 and Feature Slices A1, A2, and A3 (Customers and Catalog) are implemented and locally verified. Brightloop is a subscription-management web app for the hackathon problem statement.

Current stack: Python 3.14.4, Django 5.2.18, PostgreSQL 17.11, server-rendered HTML. Exact dependencies are pinned in requirements.txt. Syed's B1 shared UI (`arhan/shared-ui`) was merged into `main`. Abbas's A1 platform, A2 public authentication, and A3 catalog & customer views are implemented with 60 automated tests passing against PostgreSQL in ~0.7s.

## 2. Ownership and scope

Developer 1: Abbas Saeed — platform, authentication, catalog, plans, quotations, subscriptions.
Developer 2: Syed Arhan — shared UI, pricing/taxes/discounts, billing, invoices, payments, reporting.
See WORK_DIVISION.md for full responsibilities and cross-module change rules.

Current assistant merged Syed's B1 shared UI, implemented Abbas's A2 authentication scope and A3 catalog scope, and verified integration.

## 3. Repository map

Root: C:\Users\abbas\Desktop\brightloop.

- AGENTS.md: entry point both agents should read.
- README.md: setup, run, checks, configuration, limits.
- FOUNDATION.md: candidate technology/identity baseline and proposed financial policies.
- WORK_DIVISION.md / DEVELOPMENT_GUIDE.md: ownership, milestones, scope, acceptance.
- AI_AGENT_ENGINEERING_STANDARDS.md / AI_AGENT_HANDOFF_POLICY.md: required working policies.
- must_have.md / nice_to_have.md: organizer guidance supplied by user.
- config/: settings, URL routing, WSGI/ASGI, test settings.
- accounts/: custom user, database constraints, password validator, role/query guards, admin forms, public signup/login/logout/reset, throttling, migration, tests.
- catalog/: products, priced variants, customer directory, server-side cost-price confidentiality, migration, forms, views, tests.
- core/: home, database readiness, test_ui.
- templates/:
  - base.html: responsive shell, navigation, message notices.
  - core/home.html: workspace landing page.
  - accounts/: signup, login, password reset flow templates.
  - catalog/: product list, product detail, product form, variant form, customer list, customer detail.
  - components/: form_fields.html, empty_state.html.
- core/static/brightloop/app.css: shared UI design system.
- scripts/local_postgres.py: isolated local database init/start/stop/status/check.
- requirements.in / requirements.txt / pyproject.toml / .python-version: dependency and check baseline.
- .github/workflows/checks.yml: GitHub CI workflow.
- docs/contracts/: platform.md (v0.3), shared-ui.md, financial-proposal.md.
- docs/handoffs/: abbas.md and arhan.md: scoped continuation notes.

## 4. Current status

**Implemented and verified locally:**
- Git on main branch; remote tracking origin/main at https://github.com/asaeed-git/brightloop.git.
- Merged Syed's `arhan/shared-ui` into `main`.
- A1: Platform and persistence — custom UUID/email user model, case-insensitive uniqueness, roles (`ADMIN`, `STAFF`, `CUSTOMER`), DB constraints for privilege escalation prevention.
- B1: Shared UI — base layout, responsive CSS, components, accessible form rendering.
- A2: Public authentication — public signup (forces `CUSTOMER` role), throttled login (`accounts/throttle.py`), logout, password reset flow with email links, password validator (>=9 chars, uppercase, lowercase, special character, no digit required).
- A3: Customers & Catalog — `Product` and `ProductVariant` models with decimal pricing, non-negative DB check constraints, unique variant names per product, support for variant adjustments (+560.00 example), forms and responsive views, customer directory for staff/admin, server-side guarantee excluding confidential `cost_price` from customer view.
- 60 tests pass in ~0.7s against local PostgreSQL.
- Ruff check and format pass, pip check passes, Django system check (`manage.py check`) passes with 0 issues.

**Implemented but unverified elsewhere:** macOS/Linux helper path, Vercel/hosted setup.

**In progress:** Next feature slice A4 (Plans & Quotation Templates).

**Unstarted:** Plans/templates/subscriptions (A4–A6), pricing/billing/payments/reports (B2–B6), scale/performance testing, deployment.

## 5. Technical contracts and decisions

See FOUNDATION.md, docs/contracts/platform.md, docs/contracts/shared-ui.md, and docs/contracts/financial-proposal.md.

- `is_staff` is Django admin access, not the business STAFF role. Public signup unconditionally assigns `role=CUSTOMER`.
- Product `cost_price` is confidential; views omit it for customers and anonymous users.
- Prices use Decimal with 2 decimal places and non-negative database constraints.

## 6. Recent meaningful changes

- Created `catalog` app with `Product` and `ProductVariant` models and migration `0001_initial`.
- Implemented catalog views: product list, product detail with variants table, product create/edit, variant create/edit, customer list, and customer detail.
- Enforced role permissions: product/variant mutations and customer list are staff/admin only.
- Added comprehensive tests in `catalog/tests.py` testing variant +560 pricing, database constraints, customer cost-price concealment, and role guards.
- Updated navigation in `templates/base.html`.
- Updated documentation and contracts (`platform.md`, `abbas.md`, `FOUNDATION.md`). Total test suite now 60 tests.

## 7. Open issues and risks

- Financial domain decisions in `docs/contracts/financial-proposal.md` require joint agreement with Syed before implementing billing/invoice logic.
- Local email backend uses filebased or locmem backend for development/testing; real email delivery requires SMTP credentials in production.

## 8. Next actions

1. Commit and push A3 catalog changes to `origin/main`.
2. Begin A4 (Plans & Quotation Templates):
   - Model `Plan`: billing intervals (Daily, Weekly, Monthly, Yearly), price, minimum quantity, availability dates, lifecycle flags.
   - Model `QuotationTemplate` and `QuotationTemplateLine`.
   - Forms and responsive views for Plans and Templates.

## 9. Run and verification instructions

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py check
```

## 10. Handoff checkpoint

October 31, 2026. Branch: main. All 60 tests passing against PostgreSQL. Working tree clean after committing A3.
