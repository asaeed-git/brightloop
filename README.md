# Brightloop

A subscription-management web application being built by Abbas Saeed and Syed Arhan.
The current foundation runs locally with Django and PostgreSQL. It provides an email-based
user model, admin/staff/customer roles, Django administration, password validation,
public signup/login/reset, reusable authorization helpers, catalog/customer views, and
database readiness checks. A pure shared calculator handles approved tax/discount arithmetic;
see docs/contracts/pricing.md. Subscription/quotation integration, tax/discount configuration,
billing, invoices, payments, and reports remain unimplemented. Known authentication/catalog
review findings are recorded in docs/reviews/a2-a3-review.md.

## Stack and prerequisites

- Python 3.14.4; Django 5.2.18; PostgreSQL 17 (tested on 17.11).
- HTML templates and Django forms; JavaScript only as needed. No separate frontend build.
- Exact Python dependencies are in `requirements.txt`; install those pins on both machines.
- Install PostgreSQL's server and command-line tools. Docker is not required.

Read `AGENTS.md`, `FOUNDATION.md`, `WORK_DIVISION.md`, and `HANDOFF_INSTRUCTIONS.md` before editing.

## Windows local setup

Run these commands in the project folder (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/local_postgres.py init
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

`init` creates only this project's database cluster in `.local/postgres`, listens on
`127.0.0.1:55432`, generates private credentials in ignored `.env`, and refuses to overwrite
an existing setup. It does not change your system PostgreSQL service. If PostgreSQL is not
installed at `C:\Program Files\PostgreSQL\17\bin`, set `POSTGRES_BIN` to its `bin` directory.
Do not run `init` again on this already-configured computer.

Open http://127.0.0.1:8000/ for the starter page and http://127.0.0.1:8000/admin/ to sign in
with the administrator you created. No default administrator or shared password is supplied.
The starter uses Arhan's shared responsive shell. Feature templates can follow
`docs/contracts/shared-ui.md`; subscriptions and financial screens remain unimplemented.

For later sessions:

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py start
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Stop the web server with Ctrl+C. Stop the project database with:

```powershell
.\.venv\Scripts\python.exe scripts/local_postgres.py stop
```

On macOS/Linux, use `.venv/bin/python` instead, and make PostgreSQL 17 binaries available
on PATH or set `POSTGRES_BIN`. That setup path has not yet been tested here.

If you prefer an existing database, create a dedicated database/user, copy `.env.example`
to `.env`, and fill your private values instead of running `init`. Tests need permission
to create and drop `test_brightloop`; never point tests at production credentials.
The local helper grants the development user CREATEDB for this purpose, not superuser access.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

Tests use a disposable PostgreSQL database, not SQLite. Test settings use a fast password
hasher only for tests; never use `config.test_settings` for serving the application.
`/health/` returns 200 with `{"status":"ok"}` when the database responds, or a generic 503.
It is a connectivity check, not proof that every migration or business feature is ready.

GitHub Actions configuration is included. Check its actual results in the repository's Actions tab.
Shared repository: https://github.com/asaeed-git/brightloop. Clone this baseline before creating
feature branches; do not copy private local database or environment files between machines.

## Configuration and deployment

Required environment names: `DJANGO_SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`. Optional connection/settings names are listed in `.env.example`.
Real environment variables override the local file. Never commit `.env`, `.local`, or passwords.
Each developer has a separate database; Git shares migrations and source, not live records.

Local email uses `EMAIL_BACKEND=django.core.mail.backends.filebased.EmailBackend` and writes
messages to ignored `.local/emails`; this does not deliver email. The reset workflow and
durable email outbox are still planned.

For hosting, use a hosted PostgreSQL database, private environment values, TLS, an email provider,
static asset serving, and a deployment-specific worker/scheduler. Vercel is a possible target,
but no Vercel configuration or deployment is verified yet. Production settings default to HTTPS
and secure cookies; proxy trust must be configured for the selected host rather than assumed.

See `HANDOFF_INSTRUCTIONS.md` for actual verification and next steps.
