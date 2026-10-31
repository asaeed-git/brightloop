# Platform contract v0.5 (implemented)

## Routes

| Route | Method | Response / access |
| --- | --- | --- |
| / | GET | Public HTML foundation screen; role-aware actions |
| /health/ | GET | 200 `{"status":"ok"}` if database responds; generic 503 otherwise |
| /admin/ | Django administration | Authenticated active ADMIN with Django administration permission (`is_staff=True`) |
| /accounts/signup/ | GET, POST | Public registration; always creates `CUSTOMER` role; redirects to home on success |
| /accounts/login/ | GET, POST | Session authentication; rate-limited (10/5m); email normalized |
| /accounts/logout/ | POST | Session termination; redirects to home |
| /accounts/password-reset/ | GET, POST | Rate-limited (5/10m); sends single-use token via email without leaking account existence |
| /accounts/password-reset/sent/ | GET | Confirmation page after password reset request |
| /accounts/reset/<uidb64>/<token>/ | GET, POST | Password reset confirm; validates token, sets new password |
| /accounts/reset/complete/ | GET | Password reset completion confirmation |
| /catalog/products/ | GET | Product list; public/customer sees active products; staff/admin sees all + cost prices |
| /catalog/products/new/ | GET, POST | Create product; ADMIN and STAFF only |
| /catalog/products/<uuid:pk>/ | GET | Product detail with variants; cost price excluded for customers |
| /catalog/products/<uuid:pk>/edit/ | GET, POST | Edit product; ADMIN and STAFF only |
| /catalog/products/<uuid:product_pk>/variants/new/ | GET, POST | Create product variant; ADMIN and STAFF only |
| /catalog/variants/<uuid:pk>/edit/ | GET, POST | Edit product variant; ADMIN and STAFF only |
| /catalog/customers/ | GET | Customer list; ADMIN and STAFF only |
| /catalog/customers/<uuid:pk>/ | GET | Customer detail; ADMIN and STAFF only |
| /plans/ | GET | Plan list; public/customer sees active and available plans; staff/admin sees all |
| /plans/new/ | GET, POST | Create plan; ADMIN and STAFF only |
| /plans/<uuid:pk>/ | GET | Plan detail; includes interval, minimum quantity, and lifecycle policies |
| /plans/<uuid:pk>/edit/ | GET, POST | Edit plan; ADMIN and STAFF only |
| /plans/templates/ | GET | Quotation template list; ADMIN and STAFF only |
| /plans/templates/new/ | GET, POST | Create quotation template; ADMIN and STAFF only |
| /plans/templates/<uuid:pk>/ | GET | Template detail with line items and B2 pricing preview; ADMIN and STAFF only |
| /plans/templates/<uuid:pk>/edit/ | GET, POST | Edit quotation template; ADMIN and STAFF only |
| /plans/templates/<uuid:pk>/lines/new/ | POST | Add line to quotation template; ADMIN and STAFF only |
| /plans/templates/<uuid:pk>/lines/<uuid:line_pk>/delete/ | POST | Remove line from quotation template; ADMIN and STAFF only |
| /subscriptions/ | GET | Subscription directory; customers see own records, staff/admin sees all + status tabs |
| /subscriptions/new/ | GET, POST | Create subscription draft; ADMIN and STAFF only |
| /subscriptions/from-template/ | GET, POST | Create quotation from pre-configured template; ADMIN and STAFF only |
| /subscriptions/<uuid:pk>/ | GET | Detail screen with line items, pure B2 pricing breakdown, and lifecycle action controls |
| /subscriptions/<uuid:pk>/edit/ | GET, POST | Edit subscription draft/quotation terms; ADMIN and STAFF only |
| /subscriptions/<uuid:pk>/lines/new/ | POST | Add product line item; ADMIN and STAFF only |
| /subscriptions/<uuid:pk>/lines/<uuid:line_pk>/delete/ | POST | Remove line item; ADMIN and STAFF only |
| /subscriptions/<uuid:pk>/transition/<action>/ | POST | Execute lifecycle transition (`send_quote`, `confirm`, `activate`, `pause`, `resume`, `close`, `renew`) |

Other methods return 405. All POSTs require CSRF protection.

## User and permissions

User IDs are UUIDs. Email is canonical lowercase and uniquely constrained case-insensitively. Roles:
ADMIN, STAFF, CUSTOMER. `is_staff` is a Django admin permission flag, not the internal STAFF role.
Use `settings.AUTH_USER_MODEL` for foreign keys, never import a replacement identity model.

Use `require_roles(request.user, ...)` for actions. Customer record queries use
`scope_to_customer(queryset, request.user)` before fetching an ID; default field is customer_id.
This helper permits staff/admin rows but does not decide whether a particular action is allowed.
Each caller still applies its operation's role check. Inactive/anonymous/unknown-role users are rejected.

## Catalog and Confidentiality Contract

- Products have `name`, `product_type`, `sales_price`, `cost_price`, `notes`, and `is_active`.
- `cost_price` is strictly confidential to ADMIN and STAFF. View context and templates for CUSTOMER and anonymous users MUST NEVER include `cost_price`.
- Product variants belong to a product and have `price_extra` adjustments (e.g. +560.00). `effective_sales_price` is computed as `product.sales_price + variant.price_extra`.
- Negative prices are rejected at both database constraint and form validation layers.

## Plans and Quotation Templates Contract

- `Plan` supports four billing intervals: `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`.
- `price` represents the recurring base fee per billing cycle and must be non-negative.
- `min_quantity` enforces minimum required seats/units (must be >= 1).
- Availability is bounded by optional `available_from` and `available_until` date bounds.
- Lifecycle policy flags: `can_pause`, `can_early_close`, `auto_close_on_expiry`, and `can_renew`.
- `QuotationTemplate` specifies an associated `Plan`, `validity_days`, and zero or more `QuotationTemplateLine` product items.
- Template previews consume the side-effect free `pricing.services.calculate_price` function.

## Subscriptions and Lifecycle Contract

- `Subscription` uniquely tracks customer subscriptions (`SUB-YYYYMM-XXXX`) with status transitions:
  `DRAFT` → `QUOTATION` → `CONFIRMED` → `ACTIVE` → `CLOSED`.
- Minimum seat quantity is strictly enforced on transitions out of `DRAFT`.
- Quotation validity expiration is strictly enforced: expired quotations reject confirmation until validity is extended.
- Activating a confirmed subscription initializes `start_date`, `current_period_start`, and calculates `current_period_end` according to the plan interval (DAILY, WEEKLY, MONTHLY with calendar day clamping, YEARLY).
- Upfront recurring billing interface: `next_billing_date` is initialized to `current_period_start`.
- If contractual `expiry_date` is defined, `current_period_end` clips to `expiry_date`.
- Pausing sets `is_paused = True` and records `pause_date` and reason; resuming clears them.
- Creating quotation from template duplicates lines, sets unit snapshot prices, and computes validity window.
- Pricing calculation uses `pricing.services.calculate_price` for live breakdown of base fee, line items, taxes, and discounts.
