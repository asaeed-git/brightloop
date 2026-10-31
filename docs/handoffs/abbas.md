# Abbas: A6 Customer Subscription Experience Checkpoint

Scope: A1 platform, A2 public authentication, A3 catalog & customers, A4 plans & quotation templates, A5 subscription lifecycle, A6 customer subscription experience.
Status: A1–A6 merged and verified on `main` alongside Syed's B1–B4; 168 tests pass against local PostgreSQL; ready for Syed's B5 Payments & Balances.

## Completed and verified in A6

1. **Customer Account Profile (`/accounts/profile/`)**:
   - `accounts/forms.py`: `ProfileForm` for editing `first_name` and `last_name` with standard whitespace cleaning.
   - `accounts/views.py`: `profile` view restricted to authenticated users; loads recent subscriptions and customer invoices.
   - `templates/accounts/profile.html`: Styled profile page with account info, name editing, password reset link, subscription status list, and recent invoice history.
   - `accounts/tests.py`: `ProfileTests` verifying login requirement, customer data rendering, and profile updates.

2. **Customer Subscription Self-Service Actions (`subscriptions/`)**:
   - **Quotation Acceptance**: Customers can accept/confirm valid quotations (`action='confirm'`) directly from the subscription detail page.
   - **Pause & Resume**: Customers can pause active subscriptions with reason when `can_pause=True` (`action='pause'`) and resume paused subscriptions (`action='resume'`).
   - **Early Cancellation**: Customers can cancel active subscriptions with reason when `can_early_close=True` (`action='close'`). Enforces contract lock-in when `can_early_close=False`.
   - **Seat / Line Quantity Management**: Added route and view `/subscriptions/<pk>/lines/<line_pk>/update-quantity/` allowing customers to update line quantities subject to `plan.min_quantity`.
   - **Linked Invoices Display**: `subscription_detail` prefetches and displays all issued billing invoices for that subscription, with status badges, period ranges, and amounts.
   - **Confidentiality & Access Control**: Server-side cost prices remain excluded; customers cannot view or modify other customers' subscriptions (`scope_to_customer`).
   - `subscriptions/tests.py`: 6 automated tests covering customer quote acceptance, pause/resume, early close permission and denial, line quantity updates, and plan minimum seat enforcement.

3. **Workspace Navigation & Dashboard**:
   - `templates/base.html`: Added "Account" navigation link in sidebar and topbar customer email profile link.
   - `templates/core/home.html`: Added customer quick actions card for Subscriptions, Invoices, and Account Settings.

4. **Total Verification**:
   - 168 tests pass in ~2.7s on PostgreSQL 17.11.
   - Ruff check & format: 0 errors across 93 files.
   - Django check: 0 issues.

## Next Steps for Syed (Developer 2)

- Proceed with **B5 Payments & Balances**:
  - Payment records, balance tracking, manual/simulated payment capture against issued invoices.
  - Marking `Invoice.status = 'PAID'` upon full payment and updating subscription balance.
