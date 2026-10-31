# Brightloop project handoff

## 1. Project snapshot

Foundation candidate 0.1 is implemented and locally verified. Brightloop is a subscription-management web app for the supplied hackathon problem statement.

Abbas selected Django + PostgreSQL on October 31, 2026 and authorized development. Current stack: Python 3.14.4, Django 5.2.18, PostgreSQL 17.11, server-rendered HTML. Exact dependencies are pinned in requirements.txt. This checkpoint covers A1 and initial A2 identity plumbing, not the full application or completed M0 gate. Syed's baseline review and machine setup are pending.

## 2. Ownership and scope

Developer 1: Abbas Saeed — platform, authentication, catalog, plans, quotations, subscriptions.
Developer 2: Syed Arhan — shared UI, pricing/taxes/discounts, billing, invoices, payments, reporting.
See WORK_DIVISION.md for full responsibilities and cross-module change rules.

Current assistant implemented Abbas's foundation scope only. The home page is a minimal placeholder for Syed to replace during B1. No work or approval is attributed to Syed. User-supplied requirements/policy files were preserved.

## 3. Repository map

Root: C:\Users\abbas\Desktop\brightloop.

- AGENTS.md: entry point both agents should read.
- README.md: setup, run, checks, configuration, limits.
- FOUNDATION.md: candidate technology/identity baseline and proposed financial policies.
- WORK_DIVISION.md / DEVELOPMENT_GUIDE.md: ownership, milestones, scope, acceptance.
- AI_AGENT_ENGINEERING_STANDARDS.md / AI_AGENT_HANDOFF_POLICY.md: required working policies.
- must_have.md / nice_to_have.md: organizer guidance supplied by user.
- config/: settings, URL routing, WSGI/ASGI, test settings.
- accounts/: custom user, database constraints, password validator, role/query guards, admin forms, migration, tests.
- core/: home and database readiness; tests.
- templates/core/home.html: honest, minimal starter screen.
- scripts/local_postgres.py: isolated local database init/start/stop/status/check.
- requirements.in / requirements.txt / pyproject.toml / .python-version: dependency and check baseline.
- .github/workflows/checks.yml: proposed GitHub CI, not run remotely.
- docs/contracts/platform.md: implemented identity/routes plus future JSON conventions.
- docs/handoffs/abbas.md and arhan.md: scoped continuation notes.
- Ignored .local/: private local database, credentials, future captured email.
- Ignored tmp/pdfs/statement-review.png: earlier PDF contact sheet.
- Original brief: C:\Users\abbas\Downloads\Subscription_Management_System.pdf (four pages).

## 4. Current status

**Implemented and verified locally:**
- Git initialized on main; origin is https://github.com/asaeed-git/brightloop.git. Initial review-candidate commit prepared for sharing at the user's request.
- Isolated Python environment and exact package pins.
- PostgreSQL cluster created inside .local/postgres on loopback port 55432; original system service untouched.
- Migrations applied; migration state persisted across an actual database stop/start.
- UUID/email user model, case-insensitive unique email/login, ADMIN/STAFF/CUSTOMER roles, privileged-flag constraints.
- Shared password validator, permission/query-scope helpers, Django account administration.
- Home and health endpoints; actual HTTP 200 for home, health, and anonymous admin login.
- 18 PostgreSQL-backed tests pass, including database constraint bypass attempts, auth/role checks, admin forms/pages, CSRF, health failure, and anonymous login regression.
- Ruff lint/format, pip dependency check, Django system check, migration drift check, production-mode configuration check, and static collection pass.

**Implemented but unverified elsewhere:** CI execution, Arhan's setup, macOS/Linux helper path, Vercel/hosted setup. No browser visual inspection was performed; HTTP/template behavior was checked.

**In progress:** no active feature editing at this checkpoint. Candidate baseline awaits team review.

**Unstarted:** public signup/login/logout/reset, throttling, durable email outbox, customer/staff business views, catalog/plans/templates/subscriptions, pricing/billing/payments/reports, full UI, scale/performance testing, deployment.

No administrator or customer accounts were left in the development database. Test accounts existed only in the disposable test database. Run createsuperuser interactively to create a private administrator.

## 5. Technical contracts and decisions

See FOUNDATION.md and docs/contracts/platform.md. User explicitly selected the stack; domain defaults are proposals, not approved or implemented financial behavior. Currency, pricing composition, dates, proration, discount allocation, and shortened-final-period charging need review with Syed before dependent work.

is_staff is Django admin access, not the business STAFF role. Only ADMIN may have privileged flags. Public signup must later force CUSTOMER and use password validation; low-level create_user is not a substitute for input validation. Session/CSRF authentication is the baseline.

Vercel is a possible deployment target discussed with the user. No hosting changes have been made; hosted PostgreSQL, static serving, proxy trust, email, and scheduled jobs still need configuration/verification. Do not deploy the local debug setup.

## 6. Recent meaningful changes

- Created the Django/PostgreSQL scaffold and actual initial identity migration.
- Added local setup helper, environment example, ignored-secret rules, requirements pins, tests, and CI definition.
- Added AGENTS.md, FOUNDATION.md, README.md, platform contracts, and scoped handoffs.
- A live anonymous admin login failed due to reading role on AnonymousUser. Fixed with an authenticated-user guard; regression test added; all 18 tests and live routes then passed.
- Abbas requested pushing the starter to https://github.com/asaeed-git/brightloop for Syed to clone. Remote inspection found no existing refs. Credential exclusion was checked across all 46 candidate source files with no private-credential matches. Initial commit/push is being performed at this checkpoint; verify actual Git state before resuming. No teammate approval or deployment is claimed.

## 7. Open issues and risks

- Initial baseline publication is in progress; confirm origin/main and the common commit before parallel feature implementation.
- Syed's approval and local run are pending. Shared UI is unstarted; full M0 acceptance is not claimed.
- Auth throttling/public flows and all financial correctness/concurrency work remain; do not expose the starter as a production-ready app.
- No final currency, complete domain schema, or financial contracts have been approved.
- Initial Windows-restricted database initialization stalled. It was stopped; its incomplete generated cluster was preserved at ignored .local/postgres-incomplete. A new isolated cluster then initialized successfully with permission. Do not delete/replace the active cluster while diagnosing this history.
- Local environment/database network operations required elevated tool permission in this environment. Ordinary developer PowerShell setup is documented; do not silently change to SQLite if access is denied.
- Organizer website restrictions and hackathon deadline remain unknown; source guidance came from user-provided files.

## 8. Next actions

1. Inspect real workspace/Git state and read AGENTS.md + FOUNDATION.md before editing.
2. Have Syed use this starter and README on his machine. Record actual success/approval, not an assumed reply. Resolve proposed financial contracts with a worked invoice example.
3. Confirm the initial baseline has reached origin/main, and have both developers use the same commit. Never share .env/.local/.venv or private credentials.
4. Syed begins B1 shared UI and proposes financial contracts. Abbas completes A2 public authentication/reset/throttling using shared templates and identity contracts, then proceeds to catalog/plans/subscriptions.
5. Integrate the narrow M1 customer-to-payment journey early; keep both scoped handoffs and this summary current.

## 9. Run and verification instructions

Use PowerShell in the root; README has the fresh-clone setup. This computer is already initialized.

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Run createsuperuser only when you need a new private administrator. Open /admin/ after starting the server. No default password exists.

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

Last results: all above passed; 18 tests passed in the final test run. Production-mode check also passed with DJANGO_DEBUG=false and check --deploy --fail-level WARNING; this checks configuration only, not actual HTTPS hosting. 127 static assets collected. Database restart/connectivity and migrate --check passed. Test/health HTTP checks passed. Browser visual QA, hosted CI, actual SMTP delivery, and business workflows remain untested/unimplemented.

Required configuration names: DJANGO_SECRET_KEY, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD.
Other names: DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS, POSTGRES_HOST,
POSTGRES_PORT, POSTGRES_SSLMODE, POSTGRES_BIN (helper), EMAIL_BACKEND, EMAIL_HOST, EMAIL_PORT,
EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS, DEFAULT_FROM_EMAIL. Values stay outside Git.

## 10. Handoff checkpoint

October 31, 2026 (Asia/Calcutta), preparing the initial foundation commit and authorized GitHub push on main. Use git status, git log -1, and git ls-remote origin refs/heads/main to verify publication; this file intentionally does not predict a commit hash or claim remote CI success. .env, .local, .venv, tmp, staticfiles are ignored; ignore behavior and private-credential exclusion were checked. Development web server was stopped after HTTP verification. The local PostgreSQL database is running on 127.0.0.1:55432; use scripts/local_postgres.py stop when finished. Do not assume a previous agent's process or settings remain unchanged; inspect before continuing.
