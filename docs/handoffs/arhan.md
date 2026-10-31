# Syed Arhan: incoming work

## Active local checkpoint — October 31, 2026

Cloned origin/main at 3b88994 into C:\Users\LENOVO\Desktop\brightloop\shared;
working branch arhan/shared-ui. Prior planning files remain in the parent folder.
Implemented independent B1 UI; financial rules and full M0 approval remain pending.
User authorized continuing Developer 2 development from this repository, not approval
of unspecified financial defaults. No financial implementation or schema was added.

### Changes ready for review

- templates/base.html: responsive shell, role-aware implemented navigation, notifications.
- templates/core/home.html: replacement welcome page, explicit unbuilt-feature status.
- templates/components/: bound Django form rendering and empty states.
- core/static/brightloop/app.css: shared styles via existing app static discovery;
  no global settings, auth, dependencies or migrations changed.
- core/test_ui.py: five tests covering role visibility, actual links, static discovery,
  accessible bound errors, hidden/non-field errors, and output escaping.
- docs/contracts/shared-ui.md: proposed integration interface and usage for Abbas.
- docs/contracts/financial-proposal.md: calculator boundary, allocation/rounding examples,
  final-period charging proposal and transactional requirements; no approvals claimed.

### Local setup and verification actually performed

Pinned Python 3.14.4 installed under ignored .local/python314 after verifying the official
installer's signature. The existing system Python 3.15.2 was not replaced and PATH was
not changed. Created .venv and installed the exact requirements.txt pins.
PostgreSQL 17.11 was already installed. Initialized this checkout's private cluster on
127.0.0.1:55432 with the supplied helper; credentials remain in ignored .env/.local.
No administrator account was created and the system PostgreSQL service was not changed.

Passed on this machine:
- manage.py migrate; manage.py check; manage.py makemigrations --check --dry-run.
- manage.py test --settings=config.test_settings: 23 tests, 0.696s reported by runner.
  Eighteen existing tests use PostgreSQL; five new UI rendering tests use SimpleTestCase.
- python -m ruff check .; python -m ruff format --check .; python -m pip check.
- manage.py collectstatic --noinput: 128 assets collected.
- Project database stop/start, scripts/local_postgres.py check, manage.py migrate --check:
  connectivity and persisted migration history survived restart.
- Browser: home and CSS HTTP 200, admin sign-in link opens the actual login form;
  desktop 1440px and mobile 390px inspected, no horizontal overflow at those widths.
  Screenshot: ignored tmp/ui/home-desktop.png. This is not a scale/performance test.
- git diff --check and exclusion of .env/.local/.venv/tmp confirmed.

Initial restricted dependency downloads and database connections failed due to sandbox
network permissions; reruns with granted access passed. No SQLite fallback was used.
Shared UI review by Abbas, live authenticated browser journeys, invoice screens, full
accessibility audit, business workflows and scale timings remain outstanding.

### Resume

Use .venv/Scripts/python.exe from this checkout (plain python selects system 3.15.2).
README commands apply after the local environment is created; do not run init again.
The preview server and project database were stopped after QA. Start the project
database with scripts/local_postgres.py start before running the application or tests.
User requested committing and pushing arhan/shared-ui. This checkpoint is included
in the UI commit; use git log/status and origin/arhan/shared-ui to verify publication.
No merge or remote CI result for this branch is claimed. Abbas's prior remote CI
result is not evidence for these changes.

Next: both developers review shared-ui.md and financial-proposal.md, settle the remaining
M0/domain decisions and record actual approvals/common commit. Then integrate one of
Abbas's auth forms with the UI; implement the shared calculator and quote consumer,
followed by the narrow persisted invoice/payment journey. Do not duplicate Abbas's
identity/subscription/outbox services or implement proposed financial defaults silently.

## Original incoming notes

This is an incoming handoff prepared by Abbas's agent, not a report of Syed's work or approval.

First read AGENTS.md, WORK_DIVISION.md, FOUNDATION.md, docs/contracts/platform.md, and the root
handoff. Use the same starter repository/files, not a separate Django project. Run README setup
on your machine and report actual results. Do not copy .env, .venv, or .local from Abbas's machine.

Next: review candidate foundation 0.1; confirm exact pricing/discount/final-period policies with
Abbas; develop the shared UI under templates/base.html and static/ once the baseline is accepted.
Replace the minimal home template as part of B1. Billing-related modules and domain schemas have
not been created; coordinate those before introducing independent contracts. Own B1–B6 as listed
in WORK_DIVISION.md. Record your own branch, verification, and status here when you begin.
