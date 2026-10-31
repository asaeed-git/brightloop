# Brightloop Demo Walkthrough: Step-by-Step Operator Guide

This document is your on-screen manual for recording the video demo. Follow these step-by-step clicks, URL transitions, and sample inputs while speaking the matching sections from the **Developer Voiceover Script**.

---

## Pre-Recording Checklist (2 Minutes Before Recording)

1. **Start Local PostgreSQL**:
   Open a terminal and run:
   ```powershell
   .\.venv\Scripts\python.exe scripts/local_postgres.py start
   ```
2. **Start Django Development Server**:
   ```powershell
   .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
   ```
3. **Browser Setup**:
   - Open **Browser Window 1 (Normal)** at `http://127.0.0.1:8000/` for **Staff / Admin**.
   - Open **Browser Window 2 (Incognito / Private)** at `http://127.0.0.1:8000/` for **Customer**.
   - Zoom browser to **110% or 125%** so text and numbers are crystal clear on video.
4. **Pre-created Accounts**:
   - **Admin / Staff**: `abbassaeed1603@gmail.com` (or your staff account)
   - **Customer**: `ali.asif7050@gmail.com` (or create a fresh customer via `/accounts/signup/`)
   - Password: Your configured password (e.g. `StrongPassword123!`)

---

## Scene-by-Scene Walkthrough

### Scene 1: Introduction & Landing Page (0:00 – 0:35)
- **Starting URL**: `http://127.0.0.1:8000/` (Browser Window 1, logged out)
- **Actions on screen**:
  1. Show the Brightloop home screen. Highlight the clean, minimalist typography, system readiness badge (`PostgreSQL Operational`), and role overview.
  2. Scroll down briefly to show the role-aware dashboard cards.
  3. Click **Log In** in the top navigation bar.
  4. Log in as **Staff/Admin** (`abbassaeed1603@gmail.com`).
  5. Show the updated topbar navigation: `Plans`, `Products`, `Subscriptions`, `Invoices`, `Payments`, `Reports`, `Billing Runs`.

---

### Scene 2: Product Catalog & Cost Price Confidentiality (0:35 – 1:10)
- **URL**: `http://127.0.0.1:8000/catalog/products/`
- **Actions on screen**:
  1. Click **Products** in the top navigation.
  2. Click on a product (or click **+ New Product** and create "Cloud Enterprise Suite" with Sales Price ₹1,200.00 and Cost Price ₹450.00).
  3. Point out the **Cost Price (₹450.00)** and the **Sales Price (₹1,200.00)** visible to you as Staff.
  4. Show the **Product Variants** section with price adjustments (e.g., "Dedicated IP Add-on" with `+₹560.00`).
  5. *(Optional Quick Demonstration)*: Switch to the Customer window or mention that customers only ever see the Sales Price and Variant adjustments—`cost_price` is completely stripped server-side.

---

### Scene 3: Subscription Plans & Quotation Templates (1:10 – 1:50)
- **URL**: `http://127.0.0.1:8000/plans/`
- **Actions on screen**:
  1. Click **Plans** in the navigation.
  2. Click into a Plan (e.g. "Professional Growth Plan").
  3. Highlight key business policies on screen:
     - **Billing Interval**: `MONTHLY` (or Daily, Weekly, Yearly)
     - **Base Price**: e.g., ₹2,500.00 / month
     - **Minimum Required Seats (`min_quantity`)**: e.g., `5` seats
     - **Lifecycle Policies**: `Can Pause: Yes`, `Can Early Close: Yes`
  4. Click **Quotation Templates** in the sub-menu (`/plans/templates/`).
  5. Open an existing template (or click **+ New Template** with 14-day validity).
  6. Point out the **Live Pricing Breakdown** table at the bottom of the template—it runs our pure calculation engine to display Gross, Discount, Tax, and Total before generating any customer contract.

---

### Scene 4: Generating Quotation & Customer Self-Service (1:50 – 2:50)
- **URL**: `http://127.0.0.1:8000/subscriptions/` (Admin Window)
- **Actions on screen**:
  1. Click **Subscriptions** $\rightarrow$ Click **Create from Template** (or `+ New Subscription`).
  2. Select Customer (`ali.asif7050@gmail.com`), select the Template, and click **Generate Quotation**.
  3. The subscription detail page opens with status **`QUOTATION`** and an auto-assigned number like `SUB-202610-0001`.
  4. Click **Send Quotation to Customer**. (Status updates to formal quote with validity date).
  5. **Switch to Browser Window 2 (Customer)**:
     - Log in as `ali.asif7050@gmail.com`.
     - Click **Account** (`/accounts/profile/`) to show the customer profile, subscription summary, and recent invoices.
     - Click **My Subscriptions** and open the quotation (`SUB-202610-0001`).
     - Point out the customer action banner. Click **Accept & Confirm Quotation**.
     - Status updates to **`CONFIRMED`**!
  6. **Demonstrate Minimum Seat Quantity Rule**:
     - Under Line Items, locate the seat line item and click **Update Quantity**.
     - Try entering `2` (below the minimum of `5`). Submit $\rightarrow$ Show the error message: *"Quantity cannot be less than the plan minimum required seats (5)"*.
     - Enter `8` $\rightarrow$ Submit $\rightarrow$ Successfully updated to 8 seats!
  7. **Demonstrate Pause & Resume**:
     - Click **Pause Subscription**, type reason "Seasonal maintenance", and confirm.
     - Show the **PAUSED** badge.
     - Click **Resume Subscription** $\rightarrow$ Show the badge clears back to Active.

---

### Scene 5: Recurring Billing Engine & Immutable Invoices (2:50 – 3:40)
- **URL**: `http://127.0.0.1:8000/billing/invoices/` (Switch back to Staff Window)
- **Actions on screen**:
  1. Click **Invoices** in the top navigation.
  2. Explain the recurring billing engine:
     - Show the **Billing Runs** tab (`/billing/runs/`).
     - Trigger or show an executed billing run: point out how subscriptions with `next_billing_date <= today` are evaluated atomically.
     - Mention the **anti-duplication unique database constraint** (`subscription`, `period_start`) that makes double-billing physically impossible.
  3. Click on an invoice in the list (e.g. `INV-202610-0001` for `ali.asif7050@gmail.com`).
  4. Highlight the **immutable snapshot lines**: Unit Price, Quantity, Gross, Discount, Tax, and Total.
  5. Click **Print Layout** (`/billing/invoices/<id>/print/`) to show the clean, printable invoice statement.

---

### Scene 6: Transactional Payment Settlement & Idempotency (3:40 – 4:30)
- **URL**: `http://127.0.0.1:8000/billing/my-invoices/` (Switch to Customer Window)
- **Actions on screen**:
  1. In the Customer window, click **My Invoices** (`/billing/my-invoices/`).
  2. Point out the account balance summary cards at the top:
     - **Total Invoiced**, **Total Paid**, and **Outstanding Balance**.
  3. Click **View Statement** on the confirmed invoice.
  4. Scroll down to the **Pay Statement** section:
     - Total due is, say, ₹5,400.00.
     - Change the amount to **₹2,000.00** (Partial Payment).
     - Select Method: **UPI (Instant)** or **Simulated Demo Payment**.
     - Click **Confirm & Pay ₹2,000.00**.
  5. The page reloads:
     - Status remains **`CONFIRMED`** (partially paid).
     - Amount Paid shows **₹2,000.00**; Balance Due updates to **₹3,400.00**.
     - Payment record appears in the **Payment History** table with timestamp and reference.
  6. Now pay the remaining **₹3,400.00**:
     - Click **Confirm & Pay ₹3,400.00**.
     - Status immediately flips to **`PAID`** with green badge and `Paid At` timestamp!
  7. **Switch to Staff Window $\rightarrow$ Click Payments (`/payments/`)**:
     - Show the central staff payment ledger.
     - Filter by payment method (`UPI`) or search by invoice number.
     - Point out the **Total Collected** metric box in the top-right corner.

---

### Scene 7: Executive Financial Reporting & Scale Benchmarks (4:30 – 5:15)
- **URL**: `http://127.0.0.1:8000/reporting/` (Staff Window)
- **Actions on screen**:
  1. Click **Reports** in the top navigation.
  2. Walk through the executive KPI cards:
     - **Invoiced Net Sales (ex-tax)**: Explain why this excludes tax for GAAP/statutory revenue recognition.
     - **Cash Collected**: Exact total of settled payment transactions.
     - **Outstanding Receivables**: Remaining uncollected balance on confirmed invoices.
     - **Overdue Receivables**: Aging balance past due dates.
     - **Active Subscriptions**: Point out that this strictly excludes paused accounts per our financial contract.
  3. Click the preset filter buttons: **Last 7 Days**, **Last 30 Days**, **This Month**, **All Time**. Show how the metrics update instantly without page reloads or lagging.
  4. Scroll down to show:
     - **Plan Distribution & Revenue Breakdown**
     - **Collections by Payment Channel**
  5. **Switch to Terminal**:
     Run the automated benchmark command live on screen:
     ```powershell
     .\.venv\Scripts\python.exe manage.py measure_timings
     ```
     Point out that every single view renders in **under 30 milliseconds** (well under the 2.0-second requirement)!
  6. Run the test suite:
     ```powershell
     .\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
     ```
     Show **192 tests passing in ~3.6s** with 0 errors.

---

### Scene 8: Wrap-up & Conclusion (5:15 – 5:35)
- **URL**: Return to Home Screen (`http://127.0.0.1:8000/`)
- **Actions on screen**:
  - Show the clean home interface.
  - Hover over the navigation links one last time.
  - End recording.
