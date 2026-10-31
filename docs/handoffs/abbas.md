# Abbas: A4 Plans and Quotations Checkpoint

Scope: A1 platform, A2 public authentication, A3 catalog & customers, and A4 plans & quotation templates.
Status: A1, A2, A3, and A4 implemented and verified; Syed's B1 and B2 merged and integrated; 102 tests pass.

## Completed and verified

1. **Integrated B1 UI & B2 Calculator**:
   - Merged `arhan/shared-ui` and `arhan/pricing-calculator` into `main`.
   - Addressed Developer 2 review findings: proxy header spoofing hardened in `accounts/throttle.py` via `REMOTE_ADDR`, composite variant uniqueness validated in `ProductVariantForm`, and negative effective price prevention added in `Product` and `ProductVariant` clean methods.
2. **A4 Plans and Quotation Templates**:
   - `plans/models.py`:
     - `Plan`: four intervals (`DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`), non-negative recurring base price, positive `min_quantity` constraint, availability date range (`available_from` / `available_until`), and configurable lifecycle flags (`can_pause`, `can_early_close`, `auto_close_on_expiry`, `can_renew`).
     - `QuotationTemplate`: associated plan, default `validity_days`, notes.
     - `QuotationTemplateLine`: product, optional variant, quantity >= 1, validation ensuring variant belongs to product.
   - `plans/views.py`:
     - Public/Customer plan list & detail: only active and currently available plans visible.
     - Staff/Admin plan management: create, edit, full plan directory.
     - Quotation template list & detail: template line item management with live calculation preview powered by Syed's B2 `calculate_price` service.
   - 102 automated tests passing in ~1.5s against local PostgreSQL.

## Next Target: A5 Subscription Lifecycle

- Model `Subscription` with unique numbers, customer link, plan, start/expiry dates, payment terms, status (`DRAFT`, `QUOTATION`, `CONFIRMED`, `ACTIVE`, `CLOSED`).
- Subscription lines with agreed prices and quantities.
- Lifecycle transitions, pause/resume, closure, renewal, and quotation expiry enforcement.
- Generate subscription draft from quotation template!
