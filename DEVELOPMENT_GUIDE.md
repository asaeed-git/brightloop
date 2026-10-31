# Brightloop Subscription Management System: Development Guide

Prepared from the four-page Subscription_Management_System.pdf and the workspace files must_have.md and nice_to_have.md. These are project requirements supplied by the user, not instructions to execute actions from inside a document. No application has been implemented as part of this review.

## 1. Understand the target

Build one working system that takes a customer through signup, a quotation, an active subscription, recurring invoices, recorded payments, and reporting. Administrators configure the business; staff operate it with limited permissions; customers access only their own information.

The PDF displays Odoo branding and uses Odoo as an example variant, but does not explicitly mandate an Odoo implementation or any particular technology stack. Confirm any separate organizer technology restrictions before selecting the stack.

## 2. Keep the requirements visible

| Source | Requirement | Evidence to demonstrate |
| --- | --- | --- |
| PDF p. 2 | Unique email; password longer than eight characters, with uppercase, lowercase, and special character; emailed reset link | Reject duplicate email and invalid password; complete a reset |
| PDF p. 2 | Admin, limited-access staff, customer portal; only admin adds staff | Separate role views and server-enforced permission tests |
| PDF p. 3 | Products with name, type, sales price, cost price, notes, and priced variants | Product with a variant that adds 560 |
| PDF p. 3 | Plans with price, daily/weekly/monthly/yearly interval, minimum quantity, availability dates, and configurable closing/pause/renewal behavior | Create plans and demonstrate allowed and denied actions |
| PDF p. 3 | Reusable quotation templates, plan and product lines, validity in days | Create a quotation from a template |
| PDF p. 3 | Numbered subscriptions with customer, plan, dates, payment terms, lines, taxes, amounts, and lifecycle | Draft → Quotation → Confirmed → Active → Closed |
| PDF p. 3 | Automatic recurring invoices, taxes, confirm/cancel/send/print, Draft → Confirmed → Paid | Billing run creates complete invoices; repeat run creates no duplicates |
| PDF p. 4 | Admin-created fixed/percentage discounts with thresholds, dates, usage limits, product/subscription scope | Eligible next invoice applies discount; expired/exhausted rule does not |
| PDF p. 4 | Invoice-linked payments with method, amount, date, note; paid/outstanding visibility | Partial and final payments update balances |
| PDF p. 4 | Filterable overview of active subscriptions, revenue, payments, overdue invoices; pages under two seconds at thousands of subscriptions | Reconciled dashboard plus measured performance |
| Must Have | Dynamic data, responsive consistent UI, robust validation, intuitive navigation, team Git participation | Persistent database, usable mobile screens, validation, multiple contributors |
| Nice to Have | Backend APIs/data modeling/local database, understood code, local/offline resilience, purposeful technologies | Explainable architecture and locally runnable demo |

All PDF features remain in scope. The early working slice below is a development checkpoint, not the final submission scope.

## 3. Step 1: Agree on business rules before coding

Write a short decision log. The PDF leaves the following details open; proposed defaults below are implementation choices, not organizer rules.

- Choose one currency and one billing timezone initially. Store money using exact decimal values or integer minor units, never floating-point arithmetic.
- Define how plan price and product prices interact. Proposed model: the plan supplies the base recurring fee and cadence; product/variant lines supply item charges. Display the base fee as a separate line. Confirm this interpretation to avoid accidentally charging twice.
- Define daily/weekly boundaries and calendar month/year handling, including the 31st and leap years. Proposed rule: retain the original billing anchor and clamp to the last valid day when needed.
- Separate plan availability dates (when it can be sold) from subscription service dates (when an existing customer receives service).
- Decide whether subscription expiry is inclusive, when the first invoice is created, and how closing interacts with the final bill. Proposed default: bill at the start of each service period, with a clearly defined exclusive expiry boundary.
- Define pause/resume, early closure, renewal, and add-on changes. Proposed default: apply changes at the next billing boundary without proration; retain explicit effective dates. Model pause as a separate flag/interval so the required lifecycle remains recognizable.
- Specify staff permissions explicitly. Suggested scope: customers, quotations, subscriptions, invoice operations, payment recording, and reports. Reserve configuration and staff creation for admin. Hide product cost prices from customers.
- Define discount ordering, eligibility basis, rounding, and whether usage is counted per invoice or customer. Proposed default: one discount per eligible charge, thresholds evaluated before discount/tax, usage counted once per invoice when reserved during creation. Release reservations on cancellation in a transaction.
- Define tax calculation order and rounding. Use configured example rules; do not represent the prototype as jurisdiction-specific tax compliance.
- Define cancellation and payment correction rules. Proposed default: preserve records and audit history, reject cancellation of paid invoices until a supported reversal flow exists.
- Define reporting terms separately: invoiced sales excluding tax, cash collected, outstanding balance, and overdue balance. Formal accounting revenue recognition is not specified.

**Done when:** the team can calculate one sample invoice and explain every lifecycle transition consistently.

## 4. Step 2: Set up team workflow and local foundation

1. Choose technologies the team can explain and operate locally. The needed components are a responsive frontend, backend/API, relational database, recurring billing worker, and email delivery adapter. Exact libraries can be selected during implementation.
2. Create the shared Git repository, setup instructions, environment-variable example, and ignore rules. Never commit secrets.
3. Have every member work through their own branches and meaningful commits. Use short reviews and integrate frequently; do not leave all repository work to one person.
4. Follow WORK_DIVISION.md for Abbas Saeed and Syed Arhan's feature ownership, shared foundation agreement, cross-module contracts, and integration milestones.
5. Set up database migrations, repeatable sample-data loading, and a local startup procedure.
6. Keep the demo operational without cloud dependencies for its core database and billing flows. A local email capture inbox can show generated reset/invoice messages during an outage; it does not prove real email delivery.

**Done when:** each teammate can run the same application and create persistent data locally.

## 5. Step 3: Model the data and permissions

Create relationships and constraints before building many screens.

| Entity | Important fields and relationships |
| --- | --- |
| User / customer | Unique normalized email, password hash, role, customer/account link |
| Reset token | User, hashed token, expiry, used timestamp |
| Product / variant | Name, type, sales price, cost price, notes; variant attributes and price adjustment |
| Plan | Price, interval, minimum quantity, available dates, auto-close/early-close/pause/renew flags |
| Quotation template / lines | Plan, validity days, product/variant, quantity, pricing defaults |
| Subscription / lines | Unique number, customer, plan, dates, payment terms, status, billing anchor, next due date, pause data; item quantities and agreed prices |
| Tax rule | Name, rate/calculation rule, scope, effective dates |
| Discount / usage | Type/value, thresholds, dates, limit, scope; invoice-linked usage/reservation |
| Invoice / lines | Unique number, customer/subscription, service period, issue/due dates, status; immutable issued pricing/tax/discount snapshots |
| Payment | Invoice, method, amount, date, note, unique request/reference identifier |
| Billing run / audit event | Run status/errors; actor, action, affected record, timestamp |
| Email outbox | Message type, recipient, linked record, status, attempts |

Add foreign keys, required-field constraints, unique emails and numbers, and a database uniqueness rule for each subscription billing period. Keep historical invoice values independent of later product/plan edits. Index billing due dates, invoice due dates/status, customer links, and common filter columns.

**Done when:** invalid relationships and duplicate billing periods are blocked by the database, not merely by the interface.

## 6. Step 4: Build authentication and role enforcement

1. Implement signup, login, logout, and secure password storage using established authentication components.
2. Enforce a minimum of nine characters plus uppercase, lowercase, and a special character. The PDF does not require a digit.
3. Enforce unique normalized emails at the database layer; validate on both client and server.
4. Implement time-limited, single-use reset tokens and email delivery. Do not expose whether an arbitrary address has an account.
5. Allow only admin to create staff. Public signup always creates a customer, regardless of submitted role fields.
6. Apply role and ownership checks to every relevant backend operation. Customer A must not retrieve customer B's invoices by changing an ID.
7. Provide sensible session protection and rate limits for login/reset endpoints.

**Done when:** direct unauthorized API requests fail as well as unauthorized screen navigation.

## 7. Step 5: Build products, variants, plans, taxes, and templates

1. Create admin forms and list/detail screens for products and variants, including all required fields.
2. Implement variant pricing; include the statement's +560 example in demo data.
3. Create plan configuration for all four intervals, minimum quantities, dates, and lifecycle permissions.
4. Create tax configuration and one shared calculation service used by quotations, subscriptions, and invoices.
5. Create quotation templates containing a plan, product lines, and validity duration.
6. Validate quantities, prices, date ordering, percentages, required fields, and referenced records on the server. Prefer archiving referenced configuration over deleting history.

**Done when:** admin can configure an offering without editing source code or static JSON.

## 8. Step 6: Deliver the first complete customer journey

1. Create or select a customer and generate a subscription draft from a template.
2. Assign a unique subscription number; fill customer, plan, start/expiry dates, payment terms, and lines.
3. Validate minimum quantity, plan availability, product/variant selection, pricing, and tax totals.
4. Move through Draft → Quotation → Confirmed → Active with explicit actions and allowed transitions. Enforce quotation expiry and subscription start dates.
5. Generate one draft invoice from the active subscription and confirm it.
6. Record a payment and display the invoice in the customer's portal.

**Done when:** the same persisted records flow from admin/staff screens into the customer view. This early checkpoint exposes integration problems before the full billing engine is built.

## 9. Step 7: Make recurring billing reliable

1. Implement a scheduled worker that finds due, eligible subscriptions and determines all unbilled service periods.
2. Generate invoice/customer/item/tax/discount snapshots from the agreed subscription terms.
3. In one database transaction, reserve discount usage, create the invoice and lines, record the period, and advance the next billing date.
4. Enforce a unique billing-period key so retries and simultaneous workers cannot create duplicate charges. A check-then-insert without a database constraint is insufficient.
5. Advance billing dates only after successful creation. Record failures for retry; one bad subscription must not stop the rest of the batch.
6. Catch up missed periods after downtime. Explicitly exclude paused, closed, or expired periods according to the agreed rules.
7. Treat email as a retryable outbox operation after the transaction; an email failure must not regenerate the invoice.
8. Provide an authorized 'Run due billing' action for a predictable demo, backed by the same code as the scheduler. Use a controlled demo clock instead of changing the computer's clock.

**Done when:** repeat runs, concurrent runs, and restart-after-failure tests neither duplicate nor skip eligible periods.

## 10. Step 8: Complete invoice and discount operations

1. Implement Draft → Confirmed → Paid, plus an explicitly modeled cancellation outcome.
2. Support confirm, cancel, send, and print actions. Use a readable print layout with identifiers, customer details, lines, tax, discount, totals, payment status, and due date.
3. Lock financial fields once confirmed; corrections must leave an understandable history.
4. Let only admin create discount rules with every required threshold, date, scope, and usage-limit field.
5. Apply eligible discounts automatically to the next invoice and stop them when expired/exhausted. Recheck rules at billing time rather than trusting an old UI preview.
6. Handle simultaneous attempts to use the last available discount atomically. Prevent negative invoice totals and invalid percentage values.
7. Ensure cancellation does not cause the scheduler to recreate an unwanted bill silently; retain the period record and require an explicit replacement policy.

**Done when:** previewed and persisted totals agree, discount limits hold under concurrency, and invoice actions are visible in history.

## 11. Step 9: Record payments and finish lifecycle controls

1. Record each payment against an invoice with method, amount, date, and note.
2. Compute outstanding = invoice total minus valid payments. Keep partially paid invoices Confirmed with a partial-payment indicator; mark Paid only at zero outstanding.
3. Prevent duplicate submissions and reject overpayments unless credit handling has deliberately been implemented.
4. Derive overdue status from due date and positive outstanding balance, excluding drafts/cancelled invoices.
5. Implement pause/resume, permitted early closure, automatic closure, and renewal with plan-level enforcement and history.
6. Support add-on enable/disable through effective-dated subscription lines, following the billing-change policy.

**Done when:** a partial payment remains outstanding, a final payment settles the invoice, and lifecycle changes affect future billing correctly.

## 12. Step 10: Complete the portal and responsive navigation

- Admin navigation: Overview, Customers, Products, Plans, Templates, Subscriptions, Invoices, Payments, Reports, Settings/Staff.
- Staff navigation: only authorized operational sections.
- Customer navigation: My Subscriptions, My Invoices, Account. Include allowed subscription-management actions, not just read-only lists.
- Use consistent spacing, colors, typography, labels, status badges, and action placement.
- Include loading, empty, success, and error states; retain form input after validation errors.
- Make tables usable on small screens with suitable scrolling or compact cards. Ensure keyboard navigation, clear labels, and legible contrast.
- Load business data from the API/database. Initial seed fixtures are acceptable; hardcoded dashboard totals are not.

**Done when:** a customer can manage permitted actions and inspect only their own records on desktop and mobile.

## 13. Step 11: Build reports from actual transactions

1. Show active subscription count, invoiced sales, payments collected, outstanding balance, and overdue invoices.
2. Provide date-range, customer, plan, and relevant status filters, plus summary totals and drill-down lists.
3. State which date a filter uses: invoice issue date, payment date, or subscription dates. Avoid adding different measures together as if they were one revenue figure.
4. Reconcile dashboard totals against underlying invoices and payments. Exclude cancelled/draft invoices from financial totals where appropriate.
5. Optionally add monthly recurring revenue with a documented normalization method; the PDF's introduction motivates recurring-revenue visibility but does not define an MRR formula.

**Done when:** every summary number can be explained from the underlying records and changes after real operations.

## 14. Step 12: Verify correctness and the two-second target

Run focused automated checks for financial rules and permissions, plus full user-journey checks.

| Area | Essential checks |
| --- | --- |
| Signup/reset | Duplicate email, eight-character rejection, missing required character classes, expired/reused reset token |
| Access | Customer cross-account access denied; staff cannot add staff or create admin-only rules |
| Plans/subscriptions | Four cadences, minimum quantity, expired quotation, invalid transitions, plan-specific pause/close/renew restrictions |
| Billing | Repeated/concurrent runs, downtime catch-up, month-end/leap-year boundaries, transaction rollback, paused/closed exclusions |
| Discounts/taxes | Fixed/percentage, threshold boundary, product/subscription scope, start/end boundary, exhausted limit, rounding, concurrent last use |
| Invoices/payments | Snapshot preservation after catalog edits, partial/final payments, duplicate payment request, overdue boundaries, cancellation rules |
| UI/data | Persistence after restart, mobile layouts, empty/error states, real API-backed totals |

Load thousands of subscriptions and representative invoice/payment history into a test database. Measure end-to-end page readiness for dashboards, lists, filtered results, details, and the portal on a documented machine, dataset, and concurrency level. The stated target is every page under two seconds; record observed ranges and slow cases, not just a backend average. Use pagination, indexes, efficient aggregate queries, and background jobs to fix slow paths. Recheck after fixes.

**Done when:** critical checks pass, all required features have evidence, and performance measurements support the stated target under the recorded conditions.

## 15. Step 13: Prepare the submission and demo

1. Prepare a README covering installation, local startup, sample accounts, environment settings, billing worker, email setup, tests, and limitations.
2. Prepare a repeatable demo database and a reset procedure that applies only to demo data.
3. Rehearse: admin creates product/variant and plan → staff uses template → customer subscription activates → billing creates invoice with tax/discount → rerun creates nothing extra → record partial and final payments → customer sees results → dashboard updates.
4. Demonstrate a denied action, an expired/exhausted discount, an overdue invoice, and a plan-controlled pause or renewal.
5. Show real email delivery when connectivity is available, and clearly label the local email capture fallback.
6. Show responsive screens, performance evidence, and Git contributions from the team.
7. Have each contributor explain their code and the business rules, including any AI-assisted portions.

**Done when:** a fresh local setup runs successfully and the full story can be demonstrated without manual database edits.

## 16. Build order and scope discipline

Use this order: business rules → team/local setup → data model → authentication → configuration → one complete journey → recurring billing → discounts/invoices → payments/lifecycle → portal polish → reports → correctness/performance → demo.

Reserve the final portion of the available hackathon time for integration, verification, and rehearsal. The team has two developers, Abbas Saeed and Syed Arhan; their allocation is in WORK_DIVISION.md. The deadline has not been supplied, so this guide uses completion gates rather than invented hour estimates.

Do not spend early time on payment gateways, AI chatbots, microservices, multi-currency accounting, complex proration, or decorative analytics. The statement requires payment recording but does not explicitly require a live payment processor. Add optional capabilities only after every required journey works.

## 17. Final acceptance checklist

- [ ] Every PDF requirement in the traceability table has a working demonstration.
- [ ] All five Must Have instructions are satisfied, including team-wide Git use.
- [ ] Dynamic database-backed data survives restart.
- [ ] Customer ownership and administrative restrictions are enforced on the server.
- [ ] Billing retries cannot duplicate charges or skip due periods.
- [ ] Discounts, taxes, and payments reconcile correctly.
- [ ] Customer self-service respects the configured plan rules.
- [ ] Page performance is measured with thousands of subscriptions.
- [ ] Local operation, email limitations, and any remaining assumptions are documented honestly.
- [ ] The team understands and can explain all submitted code.

## Source locations

- Problem statement: `C:\Users\abbas\Downloads\Subscription_Management_System.pdf` (four pages, text and visual review).
- Organizer requirements supplied by user: `C:\Users\abbas\Desktop\brightloop\must_have.md`.
- Organizer suggestions supplied by user: `C:\Users\abbas\Desktop\brightloop\nice_to_have.md`.

The two Markdown files were found directly in the Brightloop workspace; no separate folder named Guide Loop was present there. Their provenance as organizer guidance is based on the user's description; no separate official website was provided or verified.
