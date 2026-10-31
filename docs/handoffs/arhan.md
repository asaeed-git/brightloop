# Syed Arhan: incoming work

## Current checkpoint: B2 Tax and Discount Configuration

October 31, 2026. Branch arhan/billing-config, based on arhan/pricing-calculator (3ec3956).
Previous calculator increment was committed and pushed to origin/arhan/pricing-calculator.

Implemented `billing` app for B2 tax and discount configuration:
- `billing/models.py`:
  - `TaxRate`: name, rate (0.00–100.00), is_active flag, check constraints preventing negative or >100 rates.
  - `DiscountRule`: name, kind (FIXED / PERCENTAGE), value, scope (SUBSCRIPTION / PRODUCT), product FK, min_eligible_gross, valid_from/valid_until, max_uses, is_active. Check constraints enforce positive value, scope-product exclusivity, valid date ordering, non-negative threshold.
- `billing/forms.py`: `TaxRateForm` and `DiscountRuleForm` with cent-precision validation, percentage range guards, scope consistency checks, and date range coherence.
- `billing/views.py`: Admin/Staff-only CRUD views for Tax Rates and Discount Rules (`tax_list`, `tax_create`, `tax_edit`, `discount_list`, `discount_create`, `discount_edit`), protected by `accounts.permissions.require_roles`.
- `billing/urls.py`: nested routes mounted at `/billing/`.
- `billing/admin.py`: standard Django admin integration with filters and search.
- `billing/migrations/0001_initial.py`: generated and applied cleanly against local PostgreSQL.
- `templates/billing/`: responsive, accessible views for tax and discount lists and forms using the shared UI design system and `components/form_fields.html`.
- `templates/base.html`: added role-aware sidebar navigation links for Tax Rates and Discounts (visible to Staff/Admin).
- `billing/tests.py`: 29 comprehensive unit tests covering models, check constraints, forms, views, and permission boundaries.
- `core/test_ui.py`: added regression test verifying billing navigation visibility across all role/activity combinations.

Verification actually run:
- Applied `billing.0001_initial` migration to private local PostgreSQL cluster.
- Full test suite: 111 tests passed in ~3.4s against local PostgreSQL.
- Ruff lint (`ruff check .`) and formatting (`ruff format --check .`): all passed, 0 errors.
- Pip dependency check (`pip check`): no broken requirements found.
- Django system check (`manage.py check`): 0 issues identified.
- Static collection (`manage.py collectstatic --noinput`): 128 assets unmodified.
- Migration consistency (`makemigrations --check --dry-run`): no changes detected.

Next:
- Commit and push `arhan/billing-config` branch.
- Wait for Abbas's A4 (Plans & Quotations) to integrate the B2 calculation service with quotation previews and subscription billing lines.
- Proceed to B3 recurring billing and B4 invoice generation.

## Previous checkpoint: B2 pure calculator and A2/A3 review (committed in 3ec3956)

October 31, 2026. Branch arhan/pricing-calculator, based on origin/main a8df082.
Abbas merged our prior UI in 8979d98, then added A2 auth and A3 catalog. The workspace
was clean before creating this branch. No dependency changes or private files copied.

The user explicitly answered that both developers approved financial-proposal.md as
written, including discount allocation and final-period billing. Recorded that report
in FOUNDATION.md and the proposal; no direct message from Abbas is fabricated.

Implemented pricing/services.py: immutable Charge/Discount/LineTotal/PriceTotal values,
exact integer-cent/Fraction calculations, per-line half-up percentage/tax rounding,
stable proportional fixed-discount allocation, scope and validation guards. No database
side effects, API routes, migrations or settings changes. Contract: docs/contracts/pricing.md.
Caller services must still enforce dates/thresholds/usage, permissions and lifecycle rules.
Quote/invoice consumers do not exist yet. This is the calculator increment of B2 only.

Shared UI: fixed Customers link role precedence, variant editor active navigation,
anonymous signup/customer catalog landing actions, and narrow topbar account wrapping.
Backend findings in docs/reviews/a2-a3-review.md remain assigned to Abbas: forwarded-header
throttle bypass, duplicate variant submissions raising IntegrityError, negative effective
prices. Isolated tests reproduced all three; this branch does not alter auth/catalog logic.

Verification actually run:
- Applied catalog.0001_initial to the private local PostgreSQL cluster.
- Incoming suite: 60 tests passed, 1.534s.
- Three temporary defect reproductions passed, 0.156s (confirm defects, not correctness).
- Focused calculator/UI suite: 26 tests passed, 0.090s.
- Final suite: 81 tests passed, 1.564s. Eighteen pricing tests include 300 allocation cases.
- Ruff lint/format, pip check, Django system/migration checks and static collection passed.
- Browser: public signup, sign-in and empty catalog routes open; signup/sign-in at 320px
  have no horizontal page overflow. Full authenticated business workflows and scale timings
  were not browser-tested. Automated incoming auth/catalog tests ran in the final suite.

## Previous B1 checkpoint (historical)

Cloned origin/main at 3b88994 into C:\Users\LENOVO\Desktop\brightloop\shared;
working branch arhan/shared-ui. Prior planning files remain in the parent folder.
Implemented independent B1 UI; financial rules and full M0 approval remain pending.
User authorized continuing Developer 2 development from this repository, not approval
of unspecified financial defaults. No financial implementation or schema was added.
