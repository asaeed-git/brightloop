# Brightloop project handoff

## 1. Project snapshot

Foundation M0 and Feature Slice A2 (Public Authentication) are implemented and locally verified. Brightloop is a subscription-management web app for the supplied hackathon problem statement.

Current stack: Python 3.14.4, Django 5.2.18, PostgreSQL 17.11, server-rendered HTML. Exact dependencies are pinned in requirements.txt. Syed's B1 shared UI (`arhan/shared-ui`) was merged into `main`. Abbas's A1 platform and A2 public authentication flows are implemented and verified with 46 automated tests passing against PostgreSQL.

## 2. Ownership and scope

Developer 1: Abbas Saeed — platform, authentication, catalog, plans, quotations, subscriptions.
Developer 2: Syed Arhan — shared UI, pricing/taxes/discounts, billing, invoices, payments, reporting.
See WORK_DIVISION.md for full responsibilities and cross-module change rules.

Current assistant merged Syed's B1 shared UI, implemented Abbas's A2 authentication scope, and verified integration.

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
- core/: home, database readiness, test_ui.
- templates/:
  - base.html: responsive shell, navigation, message notices.
  - core/home.html: workspace landing page.
  - accounts/: signup, login, password reset flow templates.
  - components/: form_fields.html, empty_state.html.
- core/static/brightloop/app.css: shared UI design system.
- scripts/local_postgres.py: isolated local database init/start/stop/status/check.
- requirements.in / requirements.txt / pyproject.toml / .python-version: dependency and check baseline.
- .github/workflows/checks.yml: GitHub CI workflow.
- docs/contracts/: platform.md, shared-ui.md, financial-proposal.md.
- docs/handoffs/: abbas.md and arhan.md: scoped continuation notes.

## 4. Current status

**Implemented and verified locally:**
- Git on main branch; remote tracking origin/main at https://github.com/asaeed-git/brightloop.git.
- Merged Syed's `arhan/shared-ui` (commit 3ce13b6) into `main` (commit 8979d98).
- A1: Platform and persistence — custom UUID/email user model, case-insensitive uniqueness, roles (`ADMIN`, `STAFF`, `CUSTOMER`), DB constraints for privilege escalation prevention.
- B1: Shared UI — base layout, responsive CSS, components, accessible form rendering.
- A2: Public authentication — public signup (forces `CUSTOMER` role), throttled login (`accounts/throttle.py`), logout, password reset flow with email links, password validator (>=9 chars, uppercase, lowercase, special character, no digit required).
- 46 tests pass in ~0.5s against local PostgreSQL.
- Ruff check and format pass, pip check passes, Django system check (`manage.py check`) passes with 0 issues, 128 static assets collected.

**Implemented but unverified elsewhere:** macOS/Linux helper path, Vercel/hosted setup.

**In progress:** Next feature slice A3 (Customers and Catalog).

**Unstarted:** Customer/staff business views, catalog/plans/templates/subscriptions (A3–A6), pricing/billing/payments/reports (B2–B6), scale/performance testing, deployment.

## 5. Technical contracts and decisions

See FOUNDATION.md, docs/contracts/platform.md, docs/contracts/shared-ui.md, and docs/contracts/financial-proposal.md.

`is_staff` is Django admin access, not the business STAFF role. Public signup unconditionally assigns `role=CUSTOMER` and validates password strength using `AUTH_PASSWORD_VALIDATORS`. Session/CSRF authentication is authoritative.

Financial calculations and boundaries are proposed in `docs/contracts/financial-proposal.md` by Syed and require joint review.

## 6. Recent meaningful changes

- Merged `arhan/shared-ui` into `main`, bringing in responsive shared UI, CSS custom property system, accessible form field partials, and UI tests.
- Implemented `accounts/forms.py`, `accounts/views.py`, `accounts/urls.py`, and `accounts/throttle.py` for full public authentication.
- Added templates for signup, login, password reset, password reset done, password reset confirm, and password reset complete.
- Updated header in `templates/base.html` to render contextual user actions (Sign In / Sign Up when anonymous; role badge and Sign Out button when authenticated).
- Added comprehensive unit and integration tests in `accounts/tests.py` covering all auth flows, role assignment security, email normalization, and password reset token handling. Total suite now 46 tests.
- Updated `docs/contracts/platform.md`, `FOUNDATION.md`, and `docs/handoffs/abbas.md`.

## 7. Open issues and risks

- Financial domain decisions in `docs/contracts/financial-proposal.md` require joint agreement before implementing billing/invoice logic.
- Local email backend uses filebased or locmem backend for development/testing; real email delivery requires SMTP credentials in production.

## 8. Next actions

1. Commit and push A2 authentication changes to `origin/main`.
2. Begin A3 (Customers & Catalog):
   - Products model: name, product type, sales price, cost price, notes.
   - Product Variants model: variant name/attribute and price adjustment (+560 test case).
   - Staff/Admin forms and views to create, list, edit products and variants.
   - Customer-safe views: hide cost price from non-staff/admin.
3. Proceed to A4 (Plans & Quotation Templates).

## 9. Run and verification instructions

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py check
```

## 10. Handoff checkpoint

October 31, 2026. Branch: main. All 46 tests passing. Working tree clean after committing A2.
