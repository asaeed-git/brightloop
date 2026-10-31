# Abbas: A2 Authentication and Access Checkpoint

Scope: A1 platform foundation and A2 public authentication / identity.
Status: A1 complete; B1 shared UI merged from `arhan/shared-ui`; A2 implemented and verified.

## Completed and verified

1. **Integrated B1 UI**: Merged `arhan/shared-ui` into `main`. Base shell, design system (`app.css`), components (`form_fields.html`, `empty_state.html`), and responsive layouts integrated.
2. **A2 Public Authentication**:
   - `accounts/forms.py`: `SignupForm`, `BrightloopAuthenticationForm`, `BrightloopPasswordResetForm`, `BrightloopSetPasswordForm`.
   - `accounts/views.py` & `accounts/urls.py`: Signup, Login, Logout, Password Reset, Password Reset Confirm.
   - Password rules enforced: ≥9 chars, uppercase, lowercase, special character, no digit required.
   - Role enforcement: Public signup unconditionally sets `role=CUSTOMER`.
   - Email normalization: Canonical lowercase with case-insensitive unique matching.
   - Throttling (`accounts/throttle.py`): Cache-backed rate limiting on login (10/5m) and password reset (5/10m).
   - Email templates: Reset emails generated via `accounts/emails/password_reset.txt`.
   - Test suite: 46 automated tests passing in ~0.5s against local PostgreSQL.

## Next Target: A3 Customer & Catalog

- Model `Customer` profile / extension if needed, or link customer details.
- Products: name, type, sales price, cost price, notes.
- Product Variants: variant attributes with price adjustments (including the +560 test case from spec).
- Server-side permissions: ensure cost price is hidden from customers.
