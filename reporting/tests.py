import datetime
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from billing.models import Invoice
from payments.models import Payment
from plans.models import Plan
from reporting.services import get_financial_dashboard_metrics
from subscriptions.models import Subscription


class ReportingServiceTests(TestCase):
    def setUp(self):
        self.customer1 = User.objects.create_user(
            email="cust1@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
        )
        self.customer2 = User.objects.create_user(
            email="cust2@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
        )
        self.plan = Plan.objects.create(
            name="Starter Pro",
            code="starter-pro",
            interval=Plan.Interval.MONTHLY,
            price=Decimal("500.00"),
            is_active=True,
        )

        today = timezone.localdate()
        self.today = today

        # Subscriptions: 1 active paying, 1 active paused, 1 quotation, 1 closed
        self.sub_active = Subscription.objects.create(
            number="SUB-TEST-001",
            customer=self.customer1,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            is_paused=False,
            start_date=today - datetime.timedelta(days=30),
            current_period_start=today,
            current_period_end=today + datetime.timedelta(days=30),
            base_price=Decimal("500.00"),
        )
        self.sub_paused = Subscription.objects.create(
            number="SUB-TEST-002",
            customer=self.customer2,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            is_paused=True,
            start_date=today - datetime.timedelta(days=30),
            current_period_start=today,
            current_period_end=today + datetime.timedelta(days=30),
            base_price=Decimal("500.00"),
        )
        self.sub_quote = Subscription.objects.create(
            number="SUB-TEST-003",
            customer=self.customer1,
            plan=self.plan,
            status=Subscription.Status.QUOTATION,
            is_paused=False,
            start_date=today,
            base_price=Decimal("500.00"),
        )
        self.sub_closed = Subscription.objects.create(
            number="SUB-TEST-004",
            customer=self.customer2,
            plan=self.plan,
            status=Subscription.Status.CLOSED,
            is_paused=False,
            start_date=today - datetime.timedelta(days=60),
            base_price=Decimal("500.00"),
        )

        # Invoices:
        # 1. Fully paid invoice (Total: 1000, Net: 900, Tax: 100)
        self.inv_paid = Invoice.objects.create(
            number="INV-TEST-001",
            customer=self.customer1,
            subscription=self.sub_active,
            status=Invoice.Status.PAID,
            issue_date=today - datetime.timedelta(days=20),
            due_date=today - datetime.timedelta(days=5),
            subtotal=Decimal("1000.00"),
            discount_total=Decimal("100.00"),
            net_total=Decimal("900.00"),
            tax_total=Decimal("100.00"),
            total=Decimal("1000.00"),
            amount_paid=Decimal("1000.00"),
            paid_at=timezone.now(),
        )
        Payment.objects.create(
            invoice=self.inv_paid,
            customer=self.customer1,
            idempotency_key="key-test-p1",
            method=Payment.Method.CARD,
            amount=Decimal("1000.00"),
            paid_at=timezone.now() - datetime.timedelta(days=18),
        )

        # 2. Partially paid invoice (Total: 600, Net: 500, Paid: 200, Due: 400, Not overdue)
        self.inv_partial = Invoice.objects.create(
            number="INV-TEST-002",
            customer=self.customer2,
            subscription=self.sub_paused,
            status=Invoice.Status.CONFIRMED,
            issue_date=today - datetime.timedelta(days=5),
            due_date=today + datetime.timedelta(days=10),
            subtotal=Decimal("600.00"),
            discount_total=Decimal("100.00"),
            net_total=Decimal("500.00"),
            tax_total=Decimal("100.00"),
            total=Decimal("600.00"),
            amount_paid=Decimal("200.00"),
        )
        Payment.objects.create(
            invoice=self.inv_partial,
            customer=self.customer2,
            idempotency_key="key-test-p2",
            method=Payment.Method.UPI,
            amount=Decimal("200.00"),
            paid_at=timezone.now() - datetime.timedelta(days=4),
        )

        # 3. Unpaid overdue invoice (Total: 400, Net: 350, Paid: 0, Due: 400, Due date: 5 days ago)
        self.inv_overdue = Invoice.objects.create(
            number="INV-TEST-003",
            customer=self.customer1,
            subscription=self.sub_active,
            status=Invoice.Status.CONFIRMED,
            issue_date=today - datetime.timedelta(days=25),
            due_date=today - datetime.timedelta(days=10),
            subtotal=Decimal("400.00"),
            discount_total=Decimal("50.00"),
            net_total=Decimal("350.00"),
            tax_total=Decimal("50.00"),
            total=Decimal("400.00"),
            amount_paid=Decimal("0.00"),
        )

        # 4. Cancelled invoice (should be excluded from net sales totals)
        self.inv_cancelled = Invoice.objects.create(
            number="INV-TEST-004",
            customer=self.customer2,
            status=Invoice.Status.CANCELLED,
            issue_date=today - datetime.timedelta(days=2),
            due_date=today + datetime.timedelta(days=10),
            subtotal=Decimal("300.00"),
            discount_total=Decimal("0.00"),
            net_total=Decimal("300.00"),
            tax_total=Decimal("0.00"),
            total=Decimal("300.00"),
            amount_paid=Decimal("0.00"),
        )

    def test_metrics_reconcile_exactly_with_underlying_records(self):
        metrics = get_financial_dashboard_metrics(as_of_date=self.today)

        # Invoiced Net Sales (ex-tax) = 900 (inv_paid) + 500 (inv_partial) + 350 (inv_overdue) = 1750.00
        # (cancelled invoice 300 is excluded)
        self.assertEqual(metrics["invoiced_net_sales"], Decimal("1750.00"))
        self.assertEqual(metrics["invoiced_gross_sales"], Decimal("2000.00"))
        self.assertEqual(metrics["invoiced_tax_total"], Decimal("250.00"))
        self.assertEqual(metrics["invoiced_total"], Decimal("2000.00"))
        self.assertEqual(metrics["invoices_issued_count"], 3)

        # Collected cash = 1000 + 200 = 1200.00
        self.assertEqual(metrics["collected_cash"], Decimal("1200.00"))
        self.assertEqual(metrics["payments_count"], 2)

        # Outstanding receivables = inv_partial due (400) + inv_overdue due (400) = 800.00
        self.assertEqual(metrics["outstanding_receivables"], Decimal("800.00"))
        self.assertEqual(metrics["outstanding_count"], 2)

        # Overdue receivables = only inv_overdue (due_date was 10 days ago) = 400.00
        self.assertEqual(metrics["overdue_receivables"], Decimal("400.00"))
        self.assertEqual(metrics["overdue_count"], 1)

        # Subscriptions health: canonical definition active count excludes pauses
        self.assertEqual(metrics["active_paying_count"], 1)
        self.assertEqual(metrics["paused_count"], 1)
        self.assertEqual(metrics["quotation_count"], 1)
        self.assertEqual(metrics["closed_count"], 1)
        self.assertEqual(metrics["total_subscriptions_count"], 4)

    def test_date_range_filtering(self):
        # Filter to only the last 7 days:
        # inv_paid (issued 20d ago) is outside
        # inv_overdue (issued 25d ago) is outside
        # inv_partial (issued 5d ago) is inside (Net: 500)
        start = self.today - datetime.timedelta(days=7)
        metrics = get_financial_dashboard_metrics(start_date=start, end_date=self.today)

        self.assertEqual(metrics["invoiced_net_sales"], Decimal("500.00"))
        self.assertEqual(metrics["invoices_issued_count"], 1)
        # Payment 2 was 4 days ago (200.00)
        self.assertEqual(metrics["collected_cash"], Decimal("200.00"))


class ReportingViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPassword123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="StrongPassword123!",
            role=User.Role.STAFF,
        )
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
        )

    def test_admin_and_staff_access_dashboard(self):
        for user in [self.admin, self.staff]:
            self.client.login(email=user.email, password="StrongPassword123!")
            response = self.client.get(reverse("reporting:dashboard"))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "reporting/dashboard.html")
            self.assertIn("metrics", response.context)

    def test_customer_cannot_access_dashboard(self):
        self.client.login(email="customer@example.com", password="StrongPassword123!")
        response = self.client.get(reverse("reporting:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_preset_filters_in_dashboard_view(self):
        self.client.login(email="staff@example.com", password="StrongPassword123!")
        for preset in ["7d", "30d", "month", "all"]:
            response = self.client.get(reverse("reporting:dashboard"), {"preset": preset})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["preset"], preset)

    def test_custom_date_filtering_in_dashboard_view(self):
        self.client.login(email="staff@example.com", password="StrongPassword123!")
        response = self.client.get(
            reverse("reporting:dashboard"),
            {"preset": "custom", "start_date": "2026-10-01", "end_date": "2026-10-31"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["preset"], "custom")
        self.assertEqual(response.context["start_date"], datetime.date(2026, 10, 1))
        self.assertEqual(response.context["end_date"], datetime.date(2026, 10, 31))


class PerformanceToolingCommandTests(TestCase):
    def test_seed_scale_data_command(self):
        out = StringIO()
        call_command(
            "seed_scale_data",
            subscriptions=10,
            customers=5,
            prefix="testscale",
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn("Successfully seeded scale dataset", output)
        self.assertTrue(Subscription.objects.filter(number__startswith="SUB-TESTSCALE-").exists())

    def test_measure_timings_command(self):
        out = StringIO()
        call_command("measure_timings", stdout=out)
        output = out.getvalue()
        self.assertIn("Brightloop Performance & Scale Benchmark", output)
        self.assertIn("All measured pages satisfy the sub-2-second performance target!", output)
