# Abbas: A4 & B2 Merge and Team Sync Checkpoint

Scope: A1 platform, A2 public authentication, A3 catalog & customers, A4 plans & quotation templates, A5 subscription lifecycle.
Status: A1–A4 and B1–B2 merged on `main`; 132 tests pass; aligned with Developer 2 sync report `developer-sync-oct31.md`.

## Completed and verified

1. **Integrated B1 UI, B2 Calculator & B2 Billing Configuration**:
   - Merged `arhan/shared-ui`, `arhan/pricing-calculator`, and `arhan/billing-config` into `main`.
   - Addressed Developer 2 review findings: proxy header spoofing hardened in `accounts/throttle.py` via `REMOTE_ADDR`, composite variant uniqueness validated in `ProductVariantForm`, and negative effective price prevention added in `Product` and `ProductVariant` clean methods.
   - Merged TaxRate and DiscountRule models, forms, views, and 29 unit tests from `arhan/billing-config`.
2. **A4 Plans and Quotation Templates**:
   - `plans/models.py`:
     - `Plan`: four intervals (`DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`), non-negative recurring base price, positive `min_quantity` constraint, availability date range (`available_from` / `available_until`), and configurable lifecycle flags (`can_pause`, `can_early_close`, `auto_close_on_expiry`, `can_renew`).
     - `QuotationTemplate`: associated plan, default `validity_days`, notes.
     - `QuotationTemplateLine`: product, optional variant, quantity >= 1, validation ensuring variant belongs to product.
   - `plans/views.py`:
     - Public/Customer plan list & detail: only active and currently available plans visible.
     - Staff/Admin plan management: create, edit, full plan directory.
     - Quotation template list & detail: template line item management with live calculation preview powered by Syed's B2 `calculate_price` service.
   - Full test suite: 132 automated tests passing in ~1.9s against local PostgreSQL.
3. **Developer 2 Sync Review (`docs/handoffs/developer-sync-oct31.md`)**:
   - Reviewed Developer 2's sync report from commit `d0e4831`.
   - Confirmed 50% milestone achievement across the team.
   - Aligned on Milestone 1 interface contract for A5 / B3:
     - `Subscription`: `customer`, `plan`, `status` (`DRAFT`, `QUOTATION`, `CONFIRMED`, `ACTIVE`, `CLOSED`), `start_date`, `expiry_date`, `current_period_start`, `current_period_end`, `next_billing_date`, `payment_terms_days`, `can_pause`, `is_paused`, `auto_close_on_expiry`, `can_renew`.
     - `SubscriptionLine`: `product`, `variant`, `quantity`, `unit_price`.
     - Active billing query interface for B3: select active subscriptions where `next_billing_date <= today` for period `[current_period_start, current_period_end)`.

## Next Target: A5 Subscription Lifecycle

- Implement `subscriptions` app.
- Models: `Subscription` and `SubscriptionLine` adhering to the agreed interface.
- Template generation: create quotation from `QuotationTemplate`.
- Lifecycle transition state machine (`DRAFT` → `QUOTATION` → `CONFIRMED` → `ACTIVE` → `CLOSED`), pause/resume, early close, renew.
- Views, forms, customer and staff permissions, and unit tests.
