# Developer 2 review of a8df082

Reviewed October 31, 2026 on Syed's machine. Scope: A2 authentication, A3 catalog,
integration with B1, and preparation for B2. This is a focused review, not an exhaustive
security audit. All 60 incoming tests passed against PostgreSQL (1.534s), catalog migration
applied, lint/format/dependency/migration checks passed.

## Backend findings for Abbas

1. **High: client-controlled forwarded header bypasses throttling.**
   accounts/throttle.py:_client_ip trusts X-Forwarded-For before REMOTE_ADDR with no
   trusted-proxy boundary. A client hitting the application directly can rotate this
   header to obtain a fresh quota. Reproduced with one REMOTE_ADDR: exhaust a limit of
   one using header 198.51.100.1, then header 198.51.100.2 is allowed. Use REMOTE_ADDR
   by default and only trust forwarding through an explicitly configured trusted proxy.
   Also review get/set counter atomicity and shared-cache deployment before claiming
   multi-worker rate limiting; those concurrency cases were not run here.
2. **Medium: duplicate variant submissions raise an unhandled IntegrityError.**
   catalog/views.py:variant_create sets product after ProductVariantForm.is_valid().
   The form omits product, so composite uniqueness is not validated. Posting an existing
   variant name for the same product raised IntegrityError in a disposable transaction,
   rather than redisplaying a field error. Coordinate a form/service fix with friendly
   uniqueness validation and a transaction-safe race fallback; cover create and edit.
3. **Medium: variants can make effective sales prices negative.**
   Product sales/cost constraints do not constrain product.sales_price + price_extra.
   Reproduced a staff POST for product price 10.00 and adjustment -11.00: redirect 302,
   persisted effective price -1.00. This contradicts platform.md's nonnegative-pricing
   guarantee. Validate both variant updates and product price reductions; coordinate
   how persistence invariants will be enforced. The new calculator rejects this input,
   but the catalog defect remains open.

The three cases were executed as temporary tests in ignored tmp/review_checks.py using
the disposable test database. All three reproduction assertions passed (0.156s); that
confirms undesired behavior, not acceptance. No real customer/catalog data was created.
No auth/backend fix is silently integrated by this Developer 2 branch: Abbas owns these
modules, and security/schema contracts require coordination. This document is the handoff;
no message to Abbas has been sent.

## Developer 2 integration corrections

- Fixed Customers navigation's and/or precedence so inactive STAFF does not receive a
  management link; server authorization was already separate. Regression covers all roles.
- Keep Products navigation active while editing variants.
- Replace the old anonymous admin-only landing action with public signup; customer/staff
  landing actions now lead to the implemented catalog.
- Allow topbar account actions to wrap on narrow screens and remove inline sizing there.

## Documentation reconciliation

Incoming root handoff called M0 complete while FOUNDATION.md still marked financial
rules unapproved and Syed's machine run pending. The earlier local machine run was
already documented. During this review the user explicitly reported joint approval of
financial-proposal.md as written; FOUNDATION.md now records that evidence and distinguishes
approved policy from implemented features. B2 calculator implementation follows that
approval. Full billing, lifecycle, concurrency and performance acceptance is still pending.
