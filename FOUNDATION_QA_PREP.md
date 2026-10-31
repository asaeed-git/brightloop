# Brightloop Foundation & Architecture Q&A Preparation Guide

This guide is designed for quick reference and mastery ahead of the 7-question technical Q&A session. It provides exact technical answers, design rationale, architectural pillars, and key numbers for Brightloop.

---

## 1. Quick-Reference Cheat Sheet (Key Numbers & Exact Identifiers)

| Category | Specification |
|---|---|
| **Language & Runtime** | **Python 3.14.4** |
| **Web Framework** | **Django 5.2.18 (5.2 LTS series)** |
| **Database** | **PostgreSQL 17.11** (local isolated cluster on `127.0.0.1:55432` via `scripts/local_postgres.py`) |
| **Database Driver** | **`psycopg` 3.3.6** (modern psycopg v3 binary) |
| **Linter & Formatter** | **Ruff 0.17.3** (104 files clean, 0 lint errors, 100% formatted) |
| **Test Suite** | **184 automated tests** passing in ~3.5s against local PostgreSQL (0 failures, 0 errors) |
| **Frontend Stack** | Server-rendered Django templates + custom accessible CSS design system (`core/static/brightloop/app.css`); no Node.js/SPA build required; sub-200ms page response |
| **Roles (RBAC)** | `ADMIN`, `STAFF`, `CUSTOMER` (`accounts.User.Role`) |
| **Primary Keys** | UUIDs (`uuid.uuid4`) across all models (prevents sequential enumeration) |
| **Currency & Precision** | **INR (₹)**, exact `Decimal` with 2 decimal places (`Decimal("0.01")`); zero floating-point arithmetic |
| **Subscription Lifecycle** | `DRAFT` $\rightarrow$ `QUOTATION` $\rightarrow$ `CONFIRMED` $\rightarrow$ `ACTIVE` $\rightarrow$ `CLOSED` |
| **Invoice Lifecycle** | `DRAFT` $\rightarrow$ `CONFIRMED` $\rightarrow$ `PAID` (with `CANCELLED` terminal state) |
| **Payment Channels** | `CARD`, `UPI`, `BANK_TRANSFER`, `CASH`, `SIMULATED` |
| **Billing Intervals** | `DAILY`, `WEEKLY`, `MONTHLY` (with calendar day clamping), `YEARLY` |

---

## 2. Team Ownership & Responsibilities

| Developer | Domain | Milestones Owned & Completed |
|---|---|---|
| **Abbas Saeed (Developer 1)** | Platform Foundation, Security, Catalog, Plans, Lifecycle, Customer Experience | **A1** (Platform & DB), **A2** (Auth & RBAC), **A3** (Catalog & Customers), **A4** (Plans & Templates), **A5** (Subscription Engine), **A6** (Customer Experience & Profile) |
| **Syed Arhan (Developer 2)** | Shared UI, Financials, Billing, Invoicing, Payments, Reporting | **B1** (Shared UI System), **B2** (Pricing Calculator & Taxes/Discounts), **B3** (Recurring Billing Engine), **B4** (Invoices & Snapshots), **B5** (Payments & Balances), **B6** (Reporting & Scale) |

**Collaboration Protocol**: Both developers coordinate through documented contracts in `docs/contracts/` (`platform.md`, `financial-proposal.md`, `pricing.md`, `shared-ui.md`). Neither developer silently modifies schemas, settings, or shared interfaces without peer alignment.

---

## 3. The 7 Anticipated Q&A Questions & Comprehensive Answers

### Question 1: What is the technology stack and architecture of Brightloop, and why was it chosen?

**Answer:**
- **Stack**: Python 3.14.4, Django 5.2.18 LTS, PostgreSQL 17.11 (with `psycopg` 3.3.6), Ruff 0.17.3, and server-rendered HTML with an accessible, tokenized CSS design system.
- **Architecture**: A modular, monolithic Django application. We deliberately rejected microservices, separate single-page applications (SPAs), or Node.js build pipelines.
- **Rationale**:
  1. **Speed & Reliability**: Server-rendered HTML with Django templates delivers lightning-fast response times (< 200ms), easily exceeding the hackathon's 2-second performance target, while removing the operational complexity of client-side build steps, hydrating states, and CORS issues.
  2. **Relational Integrity**: Subscription management is inherently relational and financial. Django's robust ORM paired with PostgreSQL gives us native ACID transactions, row-level locks (`select_for_update`), declarative check constraints, and unique compound constraints.
  3. **Strict Local PostgreSQL Policy**: We use real local PostgreSQL for all development and tests (never SQLite). SQLite lacks PostgreSQL's strict locking semantics, concurrency isolation, and specific regex/case-insensitive constraints, making tests on SQLite unreliable for financial guarantees.

---

### Question 2: How is Authentication, Role-Based Access Control (RBAC), and Customer Data Isolation handled?

**Answer:**
- **Custom User Model (`accounts.User`)**:
  - Uses UUID primary keys and canonical lowercase, case-insensitively unique emails (`CIText` / unique functional index).
  - Explicit roles: `ADMIN`, `STAFF`, `CUSTOMER`. New signups default to `CUSTOMER`.
  - Django's built-in `is_staff` flag is strictly reserved for Django admin access by `ADMIN` users; internal operational workflows use business views guarded by the `STAFF` role.
- **Password Security**: Requires a minimum of 9 characters, both uppercase and lowercase letters, and at least one non-whitespace special character.
- **Authorization Enforcement (`accounts.permissions`)**:
  - **`require_roles(user, *roles)`**: Shared view decorator/helper that enforces role whitelisting at the view boundary. Unauthenticated users are redirected to login; unauthorized users receive an HTTP 403 Forbidden.
  - **`scope_to_customer(queryset, user, field="customer")`**: Prevents Insecure Direct Object References (IDOR). If the user is a `CUSTOMER`, querysets are strictly filtered to `customer_id=user.pk`. Staff and Admin pass through. Any attempt by Customer A to query or pay Customer B's subscription or invoice results in an immediate HTTP 404 (or 403).
- **Catalog Confidentiality**: The `cost_price` of products is strictly confidential. View contexts and templates for customers and anonymous users completely omit `cost_price`. Only Staff and Admin can view cost figures.

---

### Question 3: How does the system handle financial precision, pricing composition, taxes, and discount allocation?

**Answer:**
- **Pure Arithmetic Boundary (`pricing.services.calculate_price`)**:
  - The pricing engine is a pure, side-effect-free service. It receives stable charge IDs, quantities, unit prices, variant adjustments, tax rates, and eligible discounts, and outputs an immutable calculation breakdown.
  - **Zero Floats**: All money calculations use Python's `Decimal` with two decimal places (`Decimal("0.01")`). We never use floating-point types (`float`), avoiding binary rounding drift.
- **Price Composition**:
  - $\text{Gross} = \text{Plan Base Fee} + \sum (\text{Line Quantity} \times (\text{Product Sales Price} + \text{Variant Price Adjustment}))$.
  - The plan base fee is treated as an explicit line item.
- **Discount & Rounding Rules**:
  - **No Stacking**: At most one eligible discount per charge.
  - **Percentage Discounts**: Calculated per-line and rounded using `ROUND_HALF_UP` to the nearest cent (0.01 INR).
  - **Fixed Discounts**: Allocated proportionally across eligible gross charges using the **largest remainder method in integer cents** (Hare-Niemeyer quota):
    1. Floor each line's exact share to whole cents.
    2. Distribute remaining cents one by one to lines with the largest fractional remainders.
    3. Ties are broken deterministically by stable charge ID.
  - **Taxes**: Applied to discounted taxable net on a per-line basis using `ROUND_HALF_UP` to 0.01 INR. Invoice totals are computed by summing rounded line amounts, ensuring line items match the invoice total exactly with no off-by-one cent discrepancies.

---

### Question 4: How does the Subscription Lifecycle work, and how are business constraints (like minimum seats and pauses) enforced?

**Answer:**
- **Finite State Machine (FSM)**:
  - `DRAFT` $\rightarrow$ `QUOTATION` $\rightarrow$ `CONFIRMED` $\rightarrow$ `ACTIVE` $\rightarrow$ `CLOSED`.
  - State transitions are strictly controlled via `subscription.transition_to(action)`. Invalid jumps (e.g. `DRAFT` directly to `ACTIVE`) raise `ValidationError`.
- **Quotations**:
  - Can be generated from scratch or from reusable `QuotationTemplate`s.
  - Carries an explicit `validity_date`. Confirmation of an expired quotation is blocked unless the validity period is extended.
  - Customers can review quotations and self-serve confirm (`action='confirm'`).
- **Minimum Quantity Enforcement**:
  - Plans define `min_quantity` (minimum required seats).
  - Enforced server-side when transitioning out of `DRAFT` and whenever a customer or staff modifies line quantities. Reductions below the plan minimum are rejected with an explicit error.
- **Pausing & Early Close**:
  - Controlled by plan policy flags: `can_pause` and `can_early_close`.
  - If `can_pause=True`, subscriptions can be paused (setting `is_paused=True` and capturing the pause reason/date) and resumed without losing billing anchor integrity.
  - If `can_early_close=False`, customers cannot self-cancel mid-term, enforcing contract term lock-in.

---

### Question 5: How does the Recurring Billing Engine work, and how do you guarantee zero duplicate invoices?

**Answer:**
- **Billing Worker (`billing.services.run_recurring_billing`)**:
  - Evaluates active subscriptions where `next_billing_date <= today` and `is_paused == False`.
  - Runs in an atomic transaction per subscription (`transaction.atomic()`).
- **Immutable Invoice Snapshots**:
  - Invoices take a permanent, frozen snapshot of the subscription and catalog state.
  - `InvoiceLine` stores frozen unit price, quantity, gross, discount, tax, and net totals. If a product's price in the catalog is changed later, past invoices remain 100% immutable and audit-compliant.
- **Anti-Duplication Database Constraint**:
  - The `Invoice` table enforces a database-level unique constraint: `models.UniqueConstraint(fields=["subscription", "period_start"], name="billing_invoice_subscription_period_uniq")`.
  - Even if two billing workers execute concurrently, PostgreSQL's unique constraint prevents double-invoicing for the same period.
- **Schedule Advancement**:
  - After creating the invoice snapshot, the worker atomically advances `current_period_start`, `current_period_end`, and `next_billing_date` according to the plan interval (DAILY, WEEKLY, MONTHLY, YEARLY).
  - **Calendar Anchor Clamping**: For monthly subscriptions starting on the 31st, months with fewer days (e.g. Feb 28, Apr 30) clamp to the last valid day of the month without losing the 31st anchor.
  - Subscriptions that reach their `expiry_date` are automatically transitioned to `CLOSED` if `auto_close_on_expiry=True`.

---

### Question 6: How are payments settled, and how do you handle concurrency, overpayment, and idempotency?

**Answer:**
- **Atomic Settlement with Row-Level Locking (`payments.services.record_payment`)**:
  - The payment operation runs within `transaction.atomic()`.
  - It acquires a row-level lock on the target invoice using `Invoice.objects.select_for_update().get(pk=invoice.pk)`.
  - This guarantees that concurrent payment submissions (e.g., from multiple browser tabs or webhook retries) are serialized, eliminating race conditions.
- **Idempotency & Replay Protection**:
  - Every payment requires an `idempotency_key` (unique indexed string/UUID).
  - **Identical Replay**: If an incoming request has an existing `idempotency_key` with the same amount and method, the service returns the existing `Payment` record without debiting the customer or altering the balance.
  - **Mismatched Conflict**: If the same key is reused with a different amount or method, the service raises `PaymentConflictError` (HTTP 409).
- **Overpayment Prevention**:
  - Checked in code: if `amount > locked_invoice.amount_due`, raises `OverpaymentError`.
  - Anchored in the database: PostgreSQL check constraint `billing_invoice_amount_paid_lte_total` (`amount_paid <= total`) guarantees that overpayment is physically impossible at the storage layer.
- **Partial vs. Full Settlement**:
  - Partial payments increment `invoice.amount_paid` and keep the invoice in `CONFIRMED` status.
  - Full payments (`amount_paid >= total`) transition status to `PAID` and record `paid_at`.

---

### Question 7: How did the two developers coordinate, and how was the codebase verified?

**Answer:**
- **Contract-First Coordination**:
  - Abbas Saeed (Developer 1) and Syed Arhan (Developer 2) authored shared contracts in `docs/contracts/` before implementing features.
  - Changes to settings, schemas, or dependencies required cross-team agreement. No developer created alternative stacks or rogue branches.
  - Main branch (`main`) is kept continuously releasable, with fast-forward merges from verified milestone branches (`arhan/shared-ui`, `arhan/billing-config`, `arhan/recurring-billing-invoices`, `arhan/payments-balances`).
- **Verification Pipeline**:
  - **184 Automated Tests**: Executed directly against local PostgreSQL 17.11 (`127.0.0.1:55432`) in 3.5 seconds. Tests cover unit logic, model constraints, multi-threaded concurrency (`select_for_update` race prevention), role guards, and customer IDOR scoping.
  - **Zero Linter Warnings**: Ruff 0.17.3 passes cleanly with 0 errors across 104 files.
  - **Zero Formatter Drift**: All 104 files formatted cleanly with Ruff.
  - **Django System Check**: 0 issues identified.
  - **Schema Synchronization**: `makemigrations --check --dry-run` confirms zero uncommitted model changes.
  - **Zero Secret Leaks**: All credentials and database files (`.local/`) are strictly kept out of git.

---

## 4. Key Terminology & Domain Enums

```
User Roles:
  ADMIN    - Platform configuration, full access, Django admin site
  STAFF    - Internal business operations (products, plans, invoices, payments)
  CUSTOMER - Self-service subscriber (view catalog, manage own subscriptions & invoices)

Subscription Statuses:
  DRAFT      - Initial creation, lines editable, minimum seat rules validated on exit
  QUOTATION  - Formal quote sent to customer with validity window
  CONFIRMED  - Quote accepted by customer or staff, ready for activation
  ACTIVE     - In service, currently billed on recurring schedule
  CLOSED     - Cancelled early, expired, or completed contract

Invoice Statuses:
  DRAFT      - Editable snapshot prior to confirmation
  CONFIRMED  - Finalized, awaiting payment; partial payments stay CONFIRMED
  PAID       - Fully settled (amount_paid == total)
  CANCELLED  - Voided

Payment Methods:
  CARD, UPI, BANK_TRANSFER, CASH, SIMULATED
```

---

## 5. One-Minute Elevator Pitch / Overview

> *"Brightloop is a production-grade subscription management and recurring billing platform built with Python 3.14, Django 5.2 LTS, and PostgreSQL 17. It features a contract-driven multi-role architecture with strict data isolation, exact decimal financial precision using Hare-Niemeyer discount allocation, an immutable snapshot-based invoicing engine with calendar clamping, and concurrency-safe payment settlement with row-level locks and idempotency protection—fully verified with 184 tests running on local PostgreSQL in 3.5 seconds."*
