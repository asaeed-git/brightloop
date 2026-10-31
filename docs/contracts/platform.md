# Platform contract v0.2 (implemented)

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

Other methods return 405. All POSTs require CSRF protection.

## User and permissions

User IDs are UUIDs. Email is canonical lowercase and uniquely constrained case-insensitively. Roles:
ADMIN, STAFF, CUSTOMER. `is_staff` is a Django admin permission flag, not the internal STAFF role.
Use `settings.AUTH_USER_MODEL` for foreign keys, never import a replacement identity model.

Use `require_roles(request.user, ...)` for actions. Customer record queries use
`scope_to_customer(queryset, request.user)` before fetching an ID; default field is customer_id.
This helper permits staff/admin rows but does not decide whether a particular action is allowed.
Each caller still applies its operation's role check. Inactive/anonymous/unknown-role users are rejected.

## Proposed future JSON convention (not implemented)

Same-origin endpoints under /api/v1/ if JSON is needed; session cookies and CSRF remain authoritative.
Use UUID strings; Decimal money strings; ISO-8601 UTC instants and YYYY-MM-DD date-only values.
Lists use page/page_size (default 25, max 100), returning items/page/page_size/total. Errors use
`{"error":{"code":"validation_error","message":"...","fields":{}}}`. Use 400 invalid input,
401 unauthenticated, 403 forbidden action, 404 inaccessible/missing record, 409 state conflict.
HTML forms use Django form errors and conventional redirects. Freeze actual endpoint contracts
with both owners before adding consumers; these conventions do not create promised routes.
