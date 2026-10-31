# Abbas: A5 Subscription Lifecycle Checkpoint

Scope: A1 platform, A2 public authentication, A3 catalog & customers, A4 plans & quotation templates, A5 subscription lifecycle.
Status: A1–A5 and B1–B2 merged and verified on `main`; 151 tests pass; unblocked Syed's B3 recurring billing worker.

## Completed and verified

1. **A5 Subscription Lifecycle (`subscriptions/`)**:
   - `subscriptions/models.py`:
     - `Subscription`: unique readable reference `number` (`SUB-YYYYMM-XXXX`), `customer`, `plan`, `status` (`DRAFT`, `QUOTATION`, `CONFIRMED`, `ACTIVE`, `CLOSED`), `base_price` (non-negative DB check constraint), `tax_rate`, `discount_rule`, `start_date`, `expiry_date` (constrained to be $\ge \text{start\_date}$), `current_period_start`, `current_period_end`, `next_billing_date`, `quotation_date`, `quotation_valid_until`, `payment_terms_days`, lifecycle policy flags (`can_pause`, `is_paused`, `pause_date`, `pause_reason`, `can_early_close`, `auto_close_on_expiry`, `can_renew`, `close_date`, `close_reason`), notes, and timestamps.
     - `SubscriptionLine`: `subscription`, `product`, `variant` (validated to belong to product), `quantity` ($\ge 1$), and `unit_price` ($\ge 0.00$).
   - `subscriptions/services.py`:
     - Clean lifecycle state machine:
       - `transition_to_quotation`: validates lines and plan minimum seat quantity; initializes `quotation_date` and `quotation_valid_until`.
       - `transition_to_confirmed`: validates quotation validity (strictly blocks expired quotations until validity is extended); transitions to Confirmed.
       - `transition_to_active`: activates subscription, computes `current_period_start`, `current_period_end` (with calendar month clamping and contract expiry clipping), sets `next_billing_date = current_period_start` (upfront billing).
       - `pause_subscription` / `resume_subscription`: respects `can_pause`, tracks pause reason and date.
       - `close_subscription`: validates `can_early_close` against contract expiry.
       - `renew_subscription`: extends `expiry_date` and can reopen closed subscriptions.
       - `create_subscription_from_template`: clones template lines, sets unit snapshot prices and validity dates.
       - `calculate_subscription_pricing`: integrates with pure B2 `calculate_price` engine to compute exact cycle totals, including base fee, lines, taxes, and eligible discounts.
   - `subscriptions/forms.py` & `subscriptions/views.py`:
     - Full role-guarded CRUD and action endpoints: create draft, create quote from template, edit terms, add/remove line items, execute lifecycle actions.
     - Customer scoping: customers only see their own subscriptions and can accept/confirm valid quotations.
   - `templates/subscriptions/`:
     - Responsive templates matching Syed's UI system (`subscription_list.html`, `subscription_detail.html`, `subscription_form.html`, `subscription_from_template.html`).
   - `subscriptions/tests.py`:
     - 18 focused unit and integration tests covering database constraints, period calculation, lifecycle transitions, pause/resume, early close restrictions, quotation expiration enforcement, template quotation generation, live pricing calculation, and access control.
2. **Total Test Suite**:
   - 151 automated tests passing in ~2.3s against local PostgreSQL 17.11.
   - 0 linter errors, clean formatting, 0 Django check issues.

## Next Target: A6 Customer Portal & Syed's B3 Recurring Billing

- B3 Recurring Billing worker can query:
  `Subscription.objects.filter(status='ACTIVE', is_paused=False, next_billing_date__lte=today)`
  to generate period invoices for `[current_period_start, current_period_end)`.
- A6 polish: dedicated customer portal self-serve views and actions.
