# Brightloop foundation: M0 review candidate 0.1

## Decision and approval state

Abbas explicitly selected **Django + PostgreSQL** in the October 31, 2026 conversation and
authorized development. This file records the initial implementation and proposed domain
contracts for review. Syed Arhan's approval and a successful run on his machine are **pending**.
The initial source baseline is commit `29149d1`, published to origin/main for team review.
Publishing this candidate does not mean the full M0 gate has passed.

## Technology baseline

| Layer | Baseline |
| --- | --- |
| Language | Python 3.14.4 |
| Web framework | Django 5.2.18 (5.2 LTS series) |
| Database | PostgreSQL 17; local verification uses 17.11 |
| Driver | psycopg / psycopg-binary 3.3.6 |
| Environment loader | python-dotenv 1.2.4 |
| Checks | Django test runner + Ruff 0.17.3 |
| CI runner | Ubuntu 24.04, pinned to support Python 3.14.4; do not use the moving ubuntu-latest label |
| Frontend | Django templates/forms, HTML/CSS, optional small JavaScript modules |
| Dependency installation | pip with exact committed requirements.txt pins |
| Packaging | One Django application; no microservices, Node build, or separate SPA |

The complete transitive pins are in requirements.txt. requirements.in records allowed update
ranges; use the pinned file for ordinary installation. Dependency updates are coordinated,
not individually refreshed on each developer's machine. Python and PostgreSQL patch updates
require rechecking both local setups and CI.

Django supplies ORM migrations, sessions, password hashing, CSRF protection, forms, and an
administration interface. These reduce foundation work for two developers. PostgreSQL is
used for development and tests as well as planned hosting so concurrency tests are meaningful.

## Architecture and ownership

| Path | Owner | Status |
| --- | --- | --- |
| config/, manage.py, scripts/, requirements*, .github/ | Abbas, cross-team review | Implemented platform |
| accounts/ | Abbas | User model, validator, permissions, admin implemented; public flows pending |
| core/ | Abbas | Home/readiness endpoints |
| templates/core/home.html | Abbas initial placeholder; Syed replaces during B1 | Minimal foundation screen |
| templates/base.html, static/ | Syed | Planned shared UI; not created |
| catalog/, plans/, subscriptions/ | Abbas | Planned modules; not created |
| pricing/, billing/, payments/, reporting/ | Syed | Planned modules; not created |
| docs/contracts/ | Each domain owner; Abbas coordinates shared contracts | Initial platform/domain drafts |

Keep views thin, validation in forms or explicit input validators, business operations in
service functions, and database constraints in models/migrations. Use the ORM and parameterized
SQL. No business calculations in templates or separately copied into JavaScript.

Root settings/schema/dependencies need coordinated edits. Source ownership does not waive the
other developer's duty to enforce permissions, write relevant tests, and explain their code.

## Implemented identity contract

- `accounts.User` uses UUID primary keys, canonical lowercase email, and password hashes.
- Email uniqueness is enforced case-insensitively in PostgreSQL; login lookup is case-insensitive.
- Roles are exactly `ADMIN`, `STAFF`, `CUSTOMER`. New users default to CUSTOMER.
- Django's `is_staff` flag means administration-site access, **not** the business STAFF role.
  Database constraints reserve privileged flags for ADMIN. Internal staff use future business views.
- Session authentication and CSRF-protected same-origin forms are the baseline; do not introduce JWT.
- Passwords require at least nine characters, upper/lowercase, and a non-whitespace special character.
  A digit is not required. Shared validators also reject common/overly similar passwords in forms.
- Low-level manager calls do not replace form/service password validation. Future signup must apply
  Django password validation and force CUSTOMER, regardless of submitted role fields.
- `accounts.permissions.require_roles` is the shared role guard. `scope_to_customer` restricts a
  queryset by customer UUID; consumers must scope before lookup and test inaccessible object IDs.
- Customer-owned domain models should reference `settings.AUTH_USER_MODEL` using `customer`.
  One login represents one customer account initially; multi-user organizations are not implemented.
- `is_active=False` blocks authentication and shared authorization helpers.

## Proposed domain decisions: review before implementation

These are concrete defaults for both developers to review, not organizer mandates or implemented features.

| Topic | Candidate default |
| --- | --- |
| Currency | INR for the demo, one currency; confirm before domain schema |
| Money | Decimal amounts, 2 decimal places; JSON decimal strings; never binary floats |
| Quantities | Positive whole seats; minimum quantity applies to product-line seat total |
| Price composition | Plan base fee plus quantity × (product price + variant adjustment); show fee as a separate line |
| Tax and discounts | At most one selected eligible discount per charge; discount before tax; half-up rounding per line |
| Discount scope | Product rule affects matching product lines; subscription rule also covers base fee; allocation must reconcile |
| Usage | One reservation per invoice/rule in the billing transaction; release on explicit cancellation; previews consume nothing |
| Time | Store timezone-aware UTC instants; billing business timezone Asia/Kolkata; date-only fields use YYYY-MM-DD |
| Billing periods | Start-inclusive/end-exclusive; upfront billing; preserve calendar anchor, clamp invalid month days |
| Lifecycle | DRAFT → QUOTATION → CONFIRMED → ACTIVE → CLOSED; separate pause fields |
| Changes | Pause/add-on changes/early close effective at next boundary; no proration initially |
| Expiry | No new period starts at/after expiry; define shortened final-period charging before worker implementation |
| Renewal | Explicit authorized renewal; plan auto-close ends on expiry; no implied automatic extension |
| Invoices | DRAFT → CONFIRMED → PAID; CANCELLED outcome; partially paid stays CONFIRMED |
| Billing safety | Unique subscription+period, transactional usage/creation/schedule updates, retries safe |
| Payments | Positive invoice-linked payments; unique request key; reject overpayment; no paid-invoice cancellation without reversal policy |
| Reports | Separate invoiced sales excluding tax, collected cash, outstanding, overdue; active count excludes pauses |

The shortened-final-period policy and discount allocation algorithm remain open. Syed owns proposing
the exact pricing function and worked examples; Abbas reviews their quote/subscription effects. No
domain tables or financial operations have been implemented on these unconfirmed assumptions.

## Operations and deployment direction

Use the README setup and test commands. Local database listens only on 127.0.0.1:55432 and stores data
under ignored .local/. Each developer has separate credentials and data. Database migrations, not
copied database folders, synchronize structure. No static JSON replaces persisted business data.

Git uses main and origin https://github.com/asaeed-git/brightloop.git. Abbas authorized sharing
the initial review candidate with Syed. Create short owned feature branches from
the reviewed baseline; cross-review before merging. CI is supplied but not remotely executed.

Vercel was discussed as a possible host. This baseline provides WSGI/ASGI entry points and external
database configuration; no deployment is claimed. Hosted database, SSL/proxy/static handling, email,
and scheduled billing must be verified for the selected hosting plan. Never store production data
in the host's local filesystem. The local helper is for developers, never the deployment entry point.

## Change protocol and next gate

Read WORK_DIVISION.md sections 5–8 before shared changes. Record the proposal, affected callers,
migration, checks, and both developers' actual agreement. Integrate producers and consumers together;
increment this candidate version and identify its commit when one exists. Do not edit applied migrations.

To pass M0: Syed reviews the stack/identity contracts, both settle the domain decisions, Syed supplies
the shared UI, the starter runs on both machines, and a common baseline commit is recorded. Feature
work that depends on unresolved contracts waits; independent setup/UI review can proceed now.
