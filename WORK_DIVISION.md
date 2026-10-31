# Brightloop: Two-Developer Work Division and AI Collaboration Rules

## 1. Team and working agreement

| Developer | Name | Primary responsibility |
| --- | --- | --- |
| Developer 1 | Abbas Saeed | Platform foundation, authentication, catalog, plans, quotations, subscription lifecycle |
| Developer 2 | Syed Arhan | Shared UI foundation, financial calculations, billing, invoices, discounts, payments, reporting |

Each developer owns the backend, screens, validation, tests, and documentation for their assigned features. Both contribute code through Git and review each other's changes. Ownership identifies the coordinator; it does not prevent the other developer from helping after an explicit handover.

This is a work allocation, not a claim that implementation exists. The stack and financial policies are still undecided. Complete the shared foundation milestone before developing dependent features independently. No timeline is assumed because the deadline and each person's availability have not been supplied.

## 2. Documents both AI agents must read

At the start of every work session, each agent reads:

1. `AI_AGENT_ENGINEERING_STANDARDS.md`.
2. `AI_AGENT_HANDOFF_POLICY.md` and `HANDOFF_INSTRUCTIONS.md`.
3. This file, `WORK_DIVISION.md`.
4. `must_have.md`, `nice_to_have.md`, and the relevant sections of `DEVELOPMENT_GUIDE.md`.
5. The approved foundation record and relevant contracts once created.

The supplied problem statement and organizer requirements define product scope. The engineering and handoff policies define working quality. This file assigns ownership. The future approved foundation record defines implementation choices; suggestions in the development guide are not automatically approved decisions. If these documents disagree, identify the conflict and resolve it with the developers before changing the affected foundation. Continue unrelated assigned work where possible.

Keep these documents in the shared repository so both agents read the same versions. A private chat decision is not a shared contract until recorded and integrated. Reading instructions once does not keep two agents synchronized; the checkpoints below are required.

## 3. Milestone 0: Establish and freeze the initial foundation together

Abbas coordinates the initial project setup. Syed reviews it and contributes the shared UI foundation. Both developers agree on the foundation; neither agent may silently choose a different stack on its branch.

Before feature work, create these shared records in one foundation change:

| Planned artifact | Coordinator | What it must contain |
| --- | --- | --- |
| `FOUNDATION.md` | Abbas; both approve | Exact runtime/framework/database/package-manager versions, architecture, directory ownership, naming, commands, environment-variable names, decisions below, foundation version and approval record |
| `docs/contracts/` | Abbas coordinates; each owns their domain contracts | API operations, request/response schemas, validation/errors, role and ownership rules, pagination/filtering, money/date formats, status values and cross-module service contracts |
| `docs/decisions/` | Proposer of each change | Material decision, reason, alternatives, impacted modules, migration/compatibility plan, actual developer approval |
| Dependency manifest and lockfile | Abbas | One agreed dependency baseline and reproducible installation |
| Shared schema and migration setup | Abbas coordinates | Relationships, constraints, indexes, migration naming/order, safe local setup |
| Shared UI primitives/theme | Syed | Colors, typography, spacing, forms, tables, badges, loading/error/empty states, responsive navigation |
| Local setup and automated checks | Abbas | Database, worker/email development setup, formatting, tests, build and any type/lint checks appropriate to the chosen stack |

These paths are planned documentation locations, not existing implementation files. Choose actual source directories after the stack is selected and record their ownership in FOUNDATION.md.

### Decisions that must be recorded

- Architecture, framework versions, package manager, database, authentication/session mechanism, email adapter, and worker execution model.
- Identity/customer relationship; admin/staff/customer permission matrix; customer-data scoping; confidential fields such as cost price.
- Canonical subscription and invoice status values and allowed transitions; pause/resume, renewal, early/automatic closure, add-on effective dates.
- Plan price versus product/variant price composition; minimum-quantity interpretation.
- Currency, exact money representation, rounding, tax/discount order, threshold basis, discount scope/stacking, usage reservation and cancellation release rules.
- Billing timezone, calendar anchors, period boundaries, first invoice, expiry behavior, catch-up, and no-proration/proration policy.
- Invoice snapshots, cancellation/replacement rules, payment deduplication, partial payments, overpayment handling, overdue logic, and reporting definitions.
- API naming, IDs, date serialization, pagination, errors, idempotency keys, and common validation conventions.
- Test fixtures, demo clock, shared sample accounts, local email fallback, and performance test conditions.

Use one worked pricing example and one lifecycle diagram/table to verify that both developers interpret the rules identically. Do not create separate rounding helpers, status enums, or pricing logic in each feature.

**Foundation gate:** both developers can install and run the same baseline; database setup works; a basic persisted request works; shared UI renders; initial checks run; both have recorded approval of the same foundation version and commit. Do not fabricate approvals. While choices are unresolved, work on requirements and agreed independent tasks rather than coding incompatible alternatives.

## 4. Detailed ownership

### Developer 1: Abbas Saeed

| Work package | Deliverables | Acceptance evidence |
| --- | --- | --- |
| A1. Platform and persistence | Project scaffold, database connection/migration framework, shared configuration, local setup, check pipeline, email delivery/outbox infrastructure | Fresh setup works; data persists after restart; actual check results documented |
| A2. Authentication and access | Signup/login/logout, unique normalized email, password rules, reset flow/email, admin-only staff creation, reusable role/customer-scope enforcement, account/staff screens | Nine-character minimum plus required character classes; invalid/duplicate input denied; expired/reused reset denied; unauthorized access denied server-side |
| A3. Customers and catalog | Customer management, products with name/type/sales price/cost price/notes, variants and price adjustments, forms/list/detail screens | Persisted editing works; +560 variant example works; customer responses exclude cost price |
| A4. Plans and quotations | Four billing intervals, plan price/minimum quantity/availability/permissions, reusable quotation templates and validity, associated screens | Every interval configurable; invalid dates/quantities rejected; template produces correct draft |
| A5. Subscription lifecycle | Unique numbers, customer/plan/start/expiry/payment terms/lines, Draft → Quotation → Confirmed → Active → Closed, pause/resume, closure, renewal, effective-dated add-ons | Invalid transitions rejected; quotation expiry enforced; plan restrictions work; billing receives agreed effective subscription data |
| A6. Customer subscription experience | My Subscriptions list/detail, allowed customer actions, account screen; integration into Syed's shared shell | Customer sees only their records; permitted management actions affect backend state |

Abbas owns authentication and subscription policy, not every caller's security tests. Syed must apply the shared enforcement to every financial endpoint and verify it.

### Developer 2: Syed Arhan

| Work package | Deliverables | Acceptance evidence |
| --- | --- | --- |
| B1. Shared UI and navigation | Common layout, role-aware menus, responsive primitives, consistent styles, form/error conventions | Desktop/mobile navigation works; Abbas can build screens using the same components |
| B2. Pricing, taxes, discounts | One authoritative financial calculation service, admin tax/discount forms, fixed/percentage rules, thresholds/dates/product-or-subscription scope/usage limits | Quote preview and invoice totals agree; boundary/rounding/scope checks pass; last remaining discount use is safe under concurrency |
| B3. Recurring billing | Due-period selection, scheduler, catch-up, transaction handling, unique period protection, run history/errors, authorized demo run using the same worker | Repeat/concurrent runs create one invoice per eligible period; restart catches up; failed transaction neither advances date nor consumes usage |
| B4. Invoices | Subscription-derived snapshots, Draft → Confirmed → Paid plus cancellation handling, staff screens, send request through shared outbox, print layout, My Invoices portal | Required details/totals correct; history survives catalog edits; confirm/cancel/send/print work; customer ownership enforced |
| B5. Payments and balances | Method/amount/date/note recording, payment list, partial/final payment handling, deduplication, outstanding and overdue views | Partial payment stays outstanding; full payment settles; duplicate/invalid/overpayment handling follows contract |
| B6. Reporting and performance tooling | Filterable active subscriptions/revenue/payments/outstanding/overdue dashboard, drill-down, repeatable scale dataset and page timing procedure | Totals reconcile with records; filters work; page timings measured with thousands of subscriptions |

Syed owns the performance measurement procedure; both developers fix slow paths in their own modules. Reports use Abbas's agreed subscription definitions, not a second interpretation of active status.

### Responsibilities shared by both

- Each implements feature-specific server validation, permissions, responsive screens, relevant tests, and documentation.
- Each reviews the other's changes and understands the decisions they approve.
- Each makes meaningful commits and participates in integration; neither is the sole Git operator.
- Both verify complete customer journeys, offline/local operation, demo readiness, and the under-two-second requirement.
- Both understand any AI-produced code and comply with actual organizer disclosure rules.
- Rebalance work at each milestone if needed. Record the task, new owner, files, current state, and handoff before switching; avoid two agents editing the same feature simultaneously.

## 5. Shared boundaries that must not drift

| Boundary | Producer / owner | Consumer | Agreement required |
| --- | --- | --- | --- |
| Identity and authorization | Abbas | Both developers' routes and screens | Current-user fields, role checks, customer ownership, unauthorized error shape |
| Financial calculation | Syed | Abbas's quotation/subscription previews and Syed's invoices | Input lines and context; exact amounts; tax/discount breakdown; validation; previews must not consume discount usage |
| Billable subscription data | Abbas | Syed's worker | IDs, status, dates, cadence, billing anchor, effective lines, terms, eligibility semantics |
| Billing schedule state | Syed's transactional billing service | Abbas's lifecycle actions | One coordinated write path/locking strategy for next-due dates and period creation; lifecycle edits cannot race billing |
| Discount reservation | Syed | Invoice creation/cancellation | Atomic reserve/release, uniqueness, rollback behavior and usage definition |
| Email infrastructure | Abbas | Reset flow and Syed's invoice delivery | Message enqueue shape, templates/attachments, retries, delivery status; reset and invoice content owned by their feature owners |
| Reporting data | Both domain owners | Syed | Included statuses, date basis, money units, tax treatment, active definition |
| UI primitives | Syed | Both developers | Shared components/theme; feature screens must not fork their own design system |

All production business data comes from the shared database/API. Temporary mocks must match the agreed contracts, be clearly marked, and be replaced before integration acceptance. Neither agent may hardcode dashboard totals as a completed feature.

## 6. Shared-file and foundation change protocol

Routine work inside an owned feature can proceed without repeated approval when it follows the accepted contracts. Changes to the stack, shared schema, authentication, global configuration, dependencies/lockfile, public API, financial rules, lifecycle definitions, shared UI interfaces, or cross-module behavior require coordination.

1. Proposer records what must change, why, affected callers/files, compatibility, migration/data impact, verification, and rollback approach in a short decision record.
2. Notify the other developer; both humans agree before integrating a foundation change. Agents must not infer the other developer's approval from silence or invent it.
3. The shared-file coordinator integrates that edit. Each feature owner may propose schema changes, but Abbas coordinates migration ordering and the central schema; Syed coordinates shared UI edits. Manifest/lockfile updates go through Abbas.
4. Implement producers and affected consumers together, or use an explicitly agreed compatible transition. Add/update contract and integration checks.
5. Update FOUNDATION.md, relevant contracts, and handoff notes. Record the new foundation version and commit after it exists.
6. Both developers synchronize to that commit and rerun affected checks before continuing dependent work. Never overwrite a teammate's local changes during synchronization.

Never rewrite an already shared/applied migration to hide a change; add an appropriate forward migration. Never resolve a lockfile/schema/contract conflict by blindly keeping one side. If an urgent bug requires a foundation change, use the same process with a focused patch; urgency does not make inconsistent foundations safe.

## 7. Integration milestones and work sequence

| Milestone | Abbas | Syed | Joint exit condition |
| --- | --- | --- | --- |
| M0: Shared baseline | Foundation/schema/auth contracts/local scaffold | UI foundation and pricing/billing contracts | Approved baseline runs on both machines; ownership and contracts recorded |
| M1: First working offering | Auth, customers, basic catalog/plan/template, activation path | Shared calculator, first invoice/payment path, minimum invoice UI | Persisted signup → quote → active subscription → invoice → payment → customer view works |
| M2: Full billing lifecycle | Remaining cadences, lifecycle controls, add-ons, subscription portal | Recurring worker, taxes/discounts, invoice operations, payment edge cases | Repeat/concurrent billing safe; lifecycle edits and billing cooperate; ownership tests pass |
| M3: Complete product | Staff/account/subscription polish; own query fixes; integration tests | Reports, invoice portal/print polish, scale measurements; own query fixes | Every required feature demonstrable; reports reconcile; responsive UI; measured performance |
| M4: Submission readiness | Fresh setup verification, technical walkthrough, README setup review | Demo data/script, financial walkthrough, performance evidence | Both rehearse the full demo; actual checks/limitations recorded; contribution history visible |

Do not wait until M3 to connect the two halves. M1 is deliberately narrow and integrated; expand it afterward. M0 and M1 dependencies take precedence over maximizing simultaneous work.

At the beginning of a work session and after each merge, exchange: current baseline commit, task ownership, changed contracts, blockers, and next integration target. Short, frequent integration is preferable to long separate branches.

## 8. Git, reviews, and handoff discipline

- Use one shared repository and an agreed stable integration branch, normally `main`. Suggested feature branch names: `abbas/<feature>` and `arhan/<feature>`.
- Both developers branch from the same accepted baseline. Keep commits small and changes scoped. Do not commit secrets or local databases with sensitive data.
- Each pull request states feature behavior, affected contracts/foundation version, migrations, checks actually run, limitations, and reviewer instructions. The other developer reviews it before integration.
- Run applicable formatting/lint/type/build checks and meaningful unit/integration tests. API/schema changes require consumer verification; financial changes require agreed example and edge-case checks.
- Use available repository branch protection/checks when configured. Written policy alone cannot technically prevent an agent from making an inconsistent change.
- Both update `HANDOFF_INSTRUCTIONS.md` on their branches as required by the handoff policy. Reconcile root handoff changes during integration; never discard the other developer's status.
- Once parallel implementation starts, keep detailed module status in `docs/handoffs/abbas.md` and `docs/handoffs/arhan.md`; the root handoff stays the current summary and entry point. These files do not yet exist.
- A handoff includes owner, branch/base commit, assigned task, changed files/contracts, actual verification, unfinished work, risks, and the next action. Do not record secrets.

## 9. Instructions to give each AI agent

### Abbas's agent

You are assisting Developer 1, Abbas Saeed. Read WORK_DIVISION.md, the engineering and handoff policies, the root handoff, and the accepted foundation/contracts before editing. Own A1–A6 and their tests/docs. Respect Syed Arhan's B1–B6 ownership. Consume the shared financial calculator and UI primitives rather than duplicating them. Coordinate shared-schema, dependency, and platform changes; do not independently change agreed financial rules. Before each session, verify the branch, real working tree, and foundation version. If the foundation is missing or unapproved, help prepare it and defer dependent implementation. Maintain accurate handoff notes and report evidence, not assumed success.

### Syed's agent

You are assisting Developer 2, Syed Arhan. Read WORK_DIVISION.md, the engineering and handoff policies, the root handoff, and the accepted foundation/contracts before editing. Own B1–B6 and their tests/docs. Respect Abbas Saeed's A1–A6 ownership. Use the shared identity, subscription contracts, database setup, and email infrastructure; do not create alternative implementations. Coordinate migration/dependency changes through Abbas and financial-contract changes with affected consumers. Before each session, verify the branch, real working tree, and foundation version. If the foundation is missing or unapproved, help prepare it and defer dependent implementation. Maintain accurate handoff notes and report evidence, not assumed success.

## 10. Definition of done

A task is complete only when its required behavior works with persisted data, appropriate access and validation are enforced, meaningful checks have actually run with results reported, connected modules still work, documentation/handoff reflect reality, and the other developer has reviewed the integrated change. Mark unverified work explicitly; do not call a mock-only screen complete.

Before submission, jointly demonstrate every PDF requirement and all Must Have instructions. Verify the same record travels through signup, quotation, activation, recurring invoice with tax/discount, partial/final payment, customer portal, and reporting. Demonstrate duplicate-billing protection, denied access, plan-controlled actions, responsive pages, local restart persistence, and measured page performance. Document any remaining limitations honestly.

## 11. Immediate next actions

1. Both read this allocation and flag any skill/availability mismatch before beginning assigned work.
2. Select the stack and resolve the foundation decisions together; record actual approvals in FOUNDATION.md.
3. Initialize the shared repository and complete M0, including exact source ownership and initial contracts.
4. Begin A2–A5 and B1–B5 in the limited M1 scope, integrating the first full customer journey before expanding features.

The first implementation milestone is a shared, approved foundation—not two independently generated applications.
