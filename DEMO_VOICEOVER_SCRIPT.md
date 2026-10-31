# Brightloop Video Demo: Developer Voiceover Script

This script is written specifically for a developer recording their own voice. Read it with a natural, conversational, and confident tone. Bracketed cues like `[CLICK ...]` indicate on-screen actions.

---

### Scene 1: Introduction & High-Level Architecture (0:00 – 0:35)

> *"Hi everyone, my name is Abbas, and today I'm excited to present Brightloop—a production-grade subscription management and recurring billing platform.*
>
> *[SHOW HOME SCREEN AT 127.0.0.1:8000]*
>
> *When designing Brightloop, we prioritized financial correctness, concurrency safety, and exceptional speed. Under the hood, Brightloop is built with Python 3.14, Django 5.2 LTS, and PostgreSQL 17.*
>
> *We deliberately avoided heavy SPA frameworks or complex client-side build pipelines. By leveraging server-rendered Django templates with a modern, accessible CSS design system, our pages load in under 30 milliseconds—easily exceeding the hackathon's performance targets.*
>
> *[LOG IN AS STAFF / ADMIN]*
>
> *Let's log in as an administrator to explore our catalog and quotation workflows."*

---

### Scene 2: Product Catalog & Confidentiality (0:35 – 1:10)

> *[CLICK PRODUCTS IN TOP NAV]*
>
> *"We'll start in the Product Catalog. Here, staff can manage both standalone products and tiered add-ons.*
>
> *[CLICK INTO 'CLOUD ENTERPRISE SUITE' OR CREATED PRODUCT]*
>
> *Notice two key architectural details here:*
>
> *First, we support dynamic product variants. Variants allow price adjustments—like this dedicated IP add-on adding ₹560 to the base price—which our pricing engine computes dynamically.*
>
> *Second, look at this Cost Price field: ₹450. In Brightloop, cost price is strictly confidential to administrators and staff. Our backend permissions and view scoping completely omit this field from customer-facing APIs and templates, preventing any data leaks."*

---

### Scene 3: Plans & Quotation Templates (1:10 – 1:50)

> *[CLICK PLANS IN TOP NAV]*
>
> *"Next, let's look at Subscription Plans. Brightloop supports four billing cadences: Daily, Weekly, Monthly, and Yearly.*
>
> *[CLICK INTO PROFESSIONAL GROWTH PLAN]*
>
> *Each plan defines critical business guardrails: a recurring base price, lifecycle flags like 'Can Pause' and 'Can Early Close', and most importantly, a minimum seat requirement (`min_quantity`). Here, it's set to 5 seats.*
>
> *[CLICK QUOTATION TEMPLATES IN SUB-NAV, THEN OPEN TEMPLATE]*
>
> *To speed up sales operations, staff can create reusable Quotation Templates. Notice this live breakdown at the bottom:*
>
> *It's powered by our pure calculation engine, which guarantees zero floating-point drift by using exact Python Decimals, Hare-Niemeyer largest-remainder discount allocation, and half-up rounding for taxes."*

---

### Scene 4: Generating Quotation & Customer Self-Service (1:50 – 2:50)

> *[CLICK SUBSCRIPTIONS -> CREATE FROM TEMPLATE]*
>
> *"Now let's create a subscription for our customer, Ali, directly from this template.*
>
> *[SELECT CUSTOMER, CLICK GENERATE QUOTATION]*
>
> *The system generates a new contract with status 'QUOTATION' and an auto-formatted number, `SUB-202610-0001`. Let's click 'Send Quotation to Customer'.*
>
> *[SWITCH TO INCOGNITO WINDOW AS CUSTOMER]*
>
> *Now, switching over to the customer's portal:*
>
> *[CLICK ACCOUNT PROFILE]*
>
> *Customers have an intuitive profile page showing their account details, active plans, and recent invoices. Under 'My Subscriptions', Ali sees the quotation we just sent.*
>
> *[OPEN QUOTATION, CLICK 'ACCEPT & CONFIRM QUOTATION']*
>
> *The customer can review the itemized breakdown and accept the quote with a single click. The status immediately transitions to 'CONFIRMED'.*
>
> *[SCROLL TO SEAT QUANTITY, CLICK UPDATE QUANTITY]*
>
> *Watch what happens if the customer tries to downgrade below the plan's 5-seat minimum:*
>
> *[ENTER 2, CLICK SUBMIT]*
>
> *The server immediately rejects the update with an explicit error. When we update it to 8 seats, it succeeds smoothly.*
>
> *[CLICK PAUSE SUBSCRIPTION, ENTER 'SEASONAL PAUSE', SUBMIT, THEN CLICK RESUME]*
>
> *Customers can also self-serve pause and resume their subscriptions without corrupting billing cycle anchors."*

---

### Scene 5: Recurring Billing Engine & Immutable Invoices (2:50 – 3:40)

> *[SWITCH BACK TO STAFF WINDOW, CLICK INVOICES]*
>
> *"Now let's look at the heart of Brightloop: the Recurring Billing Engine.*
>
> *[NAVIGATE TO BILLING RUNS TAB]*
>
> *Our billing worker runs periodically or on-demand. It scans active subscriptions where the next billing date is due, processes them in atomic database transactions, and advances the calendar schedule.*
>
> *To make double-billing physically impossible, the Invoice table enforces a unique database constraint on the subscription ID and the period start date.*
>
> *[OPEN INVOICE DETAIL]*
>
> *Every generated invoice creates an immutable snapshot of line items, frozen prices, taxes, and applied discounts. Even if a product's price in the catalog changes tomorrow, past financial statements remain completely unchanged and audit-proof.*
>
> *[CLICK PRINT LAYOUT]*
>
> *There's also a clean, printable layout ready for corporate accounting."*

---

### Scene 6: Transactional Payment Settlement & Balances (3:40 – 4:30)

> *[SWITCH TO CUSTOMER WINDOW, CLICK MY INVOICES]*
>
> *"Now let's settle this invoice. Under 'My Invoices', the customer sees their total invoiced amount, total paid, and outstanding balance.*
>
> *[OPEN INVOICE DETAIL, SCROLL TO 'PAY STATEMENT']*
>
> *Here, customers can simulate instant card or UPI payments. Let's make a partial payment first:*
>
> *[ENTER ₹2,000.00, SELECT UPI, CLICK CONFIRM & PAY]*
>
> *Our payment service uses PostgreSQL row-level locking (`select_for_update`) to prevent concurrent payment race conditions, along with unique idempotency keys to protect against duplicate submissions.*
>
> *Notice the result: the invoice remains in 'CONFIRMED' status, Amount Paid is updated to ₹2,000, and Balance Due recalculates to ₹3,400.*
>
> *[ENTER ₹3,400.00, CLICK CONFIRM & PAY]*
>
> *Now, we settle the remaining balance. As soon as the invoice is fully settled, the status transitions to 'PAID' and the settlement timestamp is recorded.*
>
> *[SWITCH TO STAFF WINDOW, CLICK PAYMENTS]*
>
> *On the staff side, every settled transaction appears in real-time in the Payments Ledger, with filters for payment channel, customer, and external bank references."*

---

### Scene 7: Executive Reporting Dashboard & Scale Benchmarks (4:30 – 5:15)

> *[CLICK REPORTS IN TOP NAV]*
>
> *"Finally, let's review the Executive Reporting Dashboard.*
>
> *[POINT OUT KPI CARDS]*
>
> *Here, leadership can track real-time business health:*
>
> *Invoiced Net Sales accurately isolates net revenue excluding statutory taxes. We also track Cash Collected, Outstanding Receivables, and Overdue Receivables.*
>
> *Notice our Active Subscriptions metric: per our financial contract, this strictly excludes paused subscriptions to reflect true paying recurring accounts.*
>
> *[CLICK 'LAST 7 DAYS', 'LAST 30 DAYS', 'ALL TIME' FILTERS]*
>
> *Filtering across different date intervals is instant.*
>
> *[SWITCH TO TERMINAL WINDOW]*
>
> *To prove our performance and scale, we built a dedicated benchmark tool:*
>
> *[RUN: `python manage.py measure_timings`]*
>
> *As you can see, every core view—from the home dashboard to invoices and catalog—renders in between 2 and 26 milliseconds, well under our 2.000-second target.*
>
> *[RUN: `python manage.py test --settings=config.test_settings`]*
>
> *And our entire automated test suite—192 tests covering concurrency, boundary math, and role security—passes 100% cleanly in just 3.6 seconds against real PostgreSQL."*

---

### Scene 8: Wrap-up & Conclusion (5:15 – 5:35)

> *[SWITCH BACK TO BRIGHTLOOP HOME SCREEN]*
>
> *"Brightloop demonstrates that you don't need heavyweight microservices or bloated JavaScript frontends to build a fast, beautiful, and mathematically rigorous financial platform.*
>
> *By combining modern Django with PostgreSQL relational rigor, we've delivered an end-to-end subscription and billing engine that is secure, audit-ready, and built to scale.*
>
> *Thank you for your time!"*
