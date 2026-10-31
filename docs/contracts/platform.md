# Platform contract v0.1 (implemented)

## Routes

| Route | Method | Response / access |
| --- | --- | --- |
| / | GET | Public HTML foundation screen; no customer data |
| /health/ | GET | 200 `{"status":"ok"}` if database responds; generic 503 otherwise |
| /admin/ | Django administration | Authenticated active ADMIN with Django administration permission |

Other methods on root/health return 405. Admin POSTs require CSRF. There are no customer API routes,
signup routes, reset routes, subscription routes, or financial endpoints yet. Do not infer them from plans.

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
