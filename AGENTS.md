# Brightloop agent entry point

Read AI_AGENT_ENGINEERING_STANDARDS.md, AI_AGENT_HANDOFF_POLICY.md,
HANDOFF_INSTRUCTIONS.md, WORK_DIVISION.md, and FOUNDATION.md (when present)
before changing code. Read the relevant docs/contracts files before changing an interface.

Abbas owns platform/auth/catalog/plans/quotations/subscriptions. Syed Arhan owns
shared UI/pricing/taxes/discounts/billing/invoices/payments/reporting. Coordinate
shared schema, dependency, security, and interface changes. Do not overwrite
another developer's work or create an alternative stack on a feature branch.

Treat an unapproved foundation as a review candidate. Never fabricate teammate
approval, tests, commits, or implementation status. Keep the root handoff current
and record scoped implementation notes in docs/handoffs when needed.

Use local PostgreSQL for development and tests. Never silently substitute SQLite
for transaction/concurrency verification. Keep secrets and local database data
out of Git. Follow README for verified setup/check commands once available.
