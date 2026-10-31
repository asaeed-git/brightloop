# Abbas: A3 Customers and Catalog Checkpoint

Scope: A1 platform foundation, A2 public authentication, and A3 customers and catalog.
Status: A1, A2, and A3 implemented and verified; 60 tests pass.

## Completed and verified

1. **A1 & B1 Integration**: Merged Syed's `arhan/shared-ui` into `main`. Base shell, design system (`app.css`), components, and responsive layouts integrated.
2. **A2 Public Authentication**:
   - `accounts/forms.py`, `accounts/views.py`, `accounts/urls.py`, `accounts/throttle.py`.
   - Signup, Login, Logout, Password reset with token email link.
   - Enforced password rules (>=9 chars, uppercase, lowercase, special character, no digit required).
   - Public signup unconditionally sets `role=CUSTOMER`.
   - Rate limiting on login and password reset.
3. **A3 Customers & Catalog**:
   - `catalog/models.py`: `Product` and `ProductVariant` models with UUID keys, decimal prices, and non-negative database check constraints.
   - Verified the specification requirement for priced variants (e.g. +560.00 variant price adjustment).
   - `catalog/views.py`: Product list, product detail, product create/edit, variant create/edit, customer list, customer detail.
   - **Cost price confidentiality**: Server-side guaranteed omission of `cost_price` in context and HTML when viewed by customers or unauthenticated visitors.
   - Role enforcement: Product and variant creation/modification and customer directory are restricted to `ADMIN` and `STAFF`.
   - Navigation updated in `templates/base.html` with role-aware Products and Customers links.
   - 60 automated tests pass against local PostgreSQL in ~0.7s.

## Next Target: A4 Plans and Quotations

- Model `Plan`: billing intervals (Daily, Weekly, Monthly, Yearly), base plan price, minimum quantity, availability date range, lifecycle policy flags (auto-close, early close, pause, renewal).
- Model `QuotationTemplate` & lines: plan, validity in days, product lines with default quantities.
- Staff/Admin forms and views for Plans and Quotation Templates.
