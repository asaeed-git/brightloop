import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from catalog.models import Product, ProductVariant
from plans.models import Plan
from subscriptions.models import Subscription, SubscriptionLine
from subscriptions.services import transition_to_active

from .forms import DiscountRuleForm, TaxRateForm
from .models import BillingRunRecord, DiscountRule, Invoice, TaxRate
from .services import (
    DuplicateBillingError,
    advance_subscription_period,
    generate_invoice_for_subscription,
    run_recurring_billing,
)


class TaxRateModelTests(TestCase):
    def test_tax_rate_creation_and_str(self):
        rate = TaxRate.objects.create(name="GST 18%", rate=Decimal("18.00"))
        self.assertEqual(str(rate), "GST 18% (18.00%)")
        self.assertTrue(rate.is_active)

    def test_tax_rate_negative_rate_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TaxRate.objects.create(name="Negative", rate=Decimal("-1.00"))

    def test_tax_rate_over_100_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TaxRate.objects.create(name="Too High", rate=Decimal("100.01"))

    def test_tax_rate_name_unique(self):
        TaxRate.objects.create(name="Standard 5%", rate=Decimal("5.00"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            TaxRate.objects.create(name="Standard 5%", rate=Decimal("5.00"))


class DiscountRuleModelTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="API Tier",
            product_type=Product.ProductType.SERVICE,
            sales_price=Decimal("1000.00"),
            cost_price=Decimal("300.00"),
        )

    def test_discount_rule_subscription_scope_creation(self):
        rule = DiscountRule.objects.create(
            name="10% Whole Sub",
            kind=DiscountRule.Kind.PERCENTAGE,
            value=Decimal("10.00"),
            scope=DiscountRule.Scope.SUBSCRIPTION,
        )
        self.assertEqual(str(rule), "10% Whole Sub (%10.00)")
        self.assertIsNone(rule.product)

    def test_discount_rule_product_scope_creation(self):
        rule = DiscountRule.objects.create(
            name="₹100 Off API Tier",
            kind=DiscountRule.Kind.FIXED,
            value=Decimal("100.00"),
            scope=DiscountRule.Scope.PRODUCT,
            product=self.product,
        )
        self.assertEqual(str(rule), "₹100 Off API Tier (₹100.00)")
        self.assertEqual(rule.product, self.product)

    def test_discount_rule_rejects_non_positive_value(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            DiscountRule.objects.create(
                name="Zero Discount",
                kind=DiscountRule.Kind.FIXED,
                value=Decimal("0.00"),
                scope=DiscountRule.Scope.SUBSCRIPTION,
            )

    def test_discount_rule_product_scope_requires_product(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            DiscountRule.objects.create(
                name="Missing Product",
                kind=DiscountRule.Kind.FIXED,
                value=Decimal("50.00"),
                scope=DiscountRule.Scope.PRODUCT,
                product=None,
            )

    def test_discount_rule_subscription_scope_no_product(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            DiscountRule.objects.create(
                name="Sub with Product",
                kind=DiscountRule.Kind.FIXED,
                value=Decimal("50.00"),
                scope=DiscountRule.Scope.SUBSCRIPTION,
                product=self.product,
            )

    def test_discount_rule_valid_date_range_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            DiscountRule.objects.create(
                name="Invalid Dates",
                kind=DiscountRule.Kind.PERCENTAGE,
                value=Decimal("5.00"),
                scope=DiscountRule.Scope.SUBSCRIPTION,
                valid_from=datetime.date(2026, 12, 31),
                valid_until=datetime.date(2026, 1, 1),
            )

    def test_discount_rule_min_eligible_gross_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            DiscountRule.objects.create(
                name="Negative Threshold",
                kind=DiscountRule.Kind.FIXED,
                value=Decimal("10.00"),
                scope=DiscountRule.Scope.SUBSCRIPTION,
                min_eligible_gross=Decimal("-50.00"),
            )


class BillingFormTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Database Add-on",
            product_type=Product.ProductType.SERVICE,
            sales_price=Decimal("500.00"),
            cost_price=Decimal("100.00"),
        )

    def test_tax_rate_form_valid(self):
        form = TaxRateForm(data={"name": "GST 18%", "rate": "18.00", "is_active": True})
        self.assertTrue(form.is_valid())

    def test_tax_rate_form_invalid_rate(self):
        form = TaxRateForm(data={"name": "Bad Rate", "rate": "120.00"})
        self.assertFalse(form.is_valid())
        self.assertIn("rate", form.errors)

    def test_discount_rule_form_valid_fixed_subscription(self):
        form = DiscountRuleForm(
            data={
                "name": "Flat 200 Off",
                "kind": DiscountRule.Kind.FIXED,
                "value": "200.00",
                "scope": DiscountRule.Scope.SUBSCRIPTION,
                "is_active": True,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_discount_rule_form_valid_percentage_product(self):
        form = DiscountRuleForm(
            data={
                "name": "15% Off Database",
                "kind": DiscountRule.Kind.PERCENTAGE,
                "value": "15.00",
                "scope": DiscountRule.Scope.PRODUCT,
                "product": str(self.product.pk),
                "is_active": True,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_discount_rule_form_percentage_out_of_range(self):
        form = DiscountRuleForm(
            data={
                "name": "Excessive Discount",
                "kind": DiscountRule.Kind.PERCENTAGE,
                "value": "105.00",
                "scope": DiscountRule.Scope.SUBSCRIPTION,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("value", form.errors)

    def test_discount_rule_form_fixed_fractional_cents_rejected(self):
        form = DiscountRuleForm(
            data={
                "name": "Sub-cent Discount",
                "kind": DiscountRule.Kind.FIXED,
                "value": "10.555",
                "scope": DiscountRule.Scope.SUBSCRIPTION,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("value", form.errors)

    def test_discount_rule_form_product_scope_requires_product(self):
        form = DiscountRuleForm(
            data={
                "name": "Missing Product Target",
                "kind": DiscountRule.Kind.FIXED,
                "value": "50.00",
                "scope": DiscountRule.Scope.PRODUCT,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("product", form.errors)

    def test_discount_rule_form_subscription_scope_rejects_product(self):
        form = DiscountRuleForm(
            data={
                "name": "Conflicting Scope",
                "kind": DiscountRule.Kind.FIXED,
                "value": "50.00",
                "scope": DiscountRule.Scope.SUBSCRIPTION,
                "product": str(self.product.pk),
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("product", form.errors)

    def test_discount_rule_form_date_range_validation(self):
        form = DiscountRuleForm(
            data={
                "name": "Inverted Dates",
                "kind": DiscountRule.Kind.FIXED,
                "value": "50.00",
                "scope": DiscountRule.Scope.SUBSCRIPTION,
                "valid_from": "2026-12-01",
                "valid_until": "2026-11-01",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("valid_until", form.errors)


class InvoiceModelTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user("inv_cust@example.com", "LongPhrase!")
        self.plan = Plan.objects.create(
            name="Starter Monthly",
            code="start-month",
            interval=Plan.Interval.MONTHLY,
            price=Decimal("500.00"),
        )
        self.subscription = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
            base_price=Decimal("500.00"),
            status=Subscription.Status.ACTIVE,
            start_date=datetime.date(2026, 1, 1),
            current_period_start=datetime.date(2026, 1, 1),
            current_period_end=datetime.date(2026, 2, 1),
            next_billing_date=datetime.date(2026, 1, 1),
        )

    def test_invoice_creation_and_properties(self):
        inv = Invoice.objects.create(
            customer=self.customer,
            subscription=self.subscription,
            status=Invoice.Status.CONFIRMED,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 2, 1),
            due_date=datetime.date(2026, 1, 15),
            subtotal=Decimal("500.00"),
            net_total=Decimal("500.00"),
            total=Decimal("500.00"),
            amount_paid=Decimal("150.00"),
        )
        self.assertTrue(inv.number.startswith("INV-"))
        self.assertEqual(inv.amount_due, Decimal("350.00"))
        # Due date is in the past compared to today -> overdue
        self.assertTrue(inv.is_overdue)

    def test_database_anti_duplication_unique_constraint(self):
        """Database constraint prevents two invoices for same subscription and period_start."""
        Invoice.objects.create(
            customer=self.customer,
            subscription=self.subscription,
            period_start=datetime.date(2026, 1, 1),
            period_end=datetime.date(2026, 2, 1),
            due_date=datetime.date(2026, 1, 15),
            total=Decimal("500.00"),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invoice.objects.create(
                customer=self.customer,
                subscription=self.subscription,
                period_start=datetime.date(2026, 1, 1),
                period_end=datetime.date(2026, 2, 1),
                due_date=datetime.date(2026, 1, 15),
                total=Decimal("500.00"),
            )

    def test_amount_paid_cannot_exceed_total_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invoice.objects.create(
                customer=self.customer,
                due_date=datetime.date(2026, 1, 15),
                total=Decimal("100.00"),
                amount_paid=Decimal("150.00"),
            )


class RecurringBillingServiceTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user("bill_user@example.com", "LongPhrase!")
        self.tax_rate = TaxRate.objects.create(name="GST 18%", rate=Decimal("18.00"))
        self.discount_rule = DiscountRule.objects.create(
            name="10% Off All",
            kind=DiscountRule.Kind.PERCENTAGE,
            value=Decimal("10.00"),
            scope=DiscountRule.Scope.SUBSCRIPTION,
        )
        self.plan = Plan.objects.create(
            name="Pro Monthly",
            code="pro-monthly",
            interval=Plan.Interval.MONTHLY,
            price=Decimal("1000.00"),
            min_quantity=1,
            auto_close_on_expiry=True,
        )
        self.product = Product.objects.create(
            name="Storage Unit",
            sales_price=Decimal("100.00"),
            cost_price=Decimal("30.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="500GB SSD",
            price_extra=Decimal("50.00"),
        )

        self.subscription = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
            base_price=self.plan.price,
            tax_rate=self.tax_rate,
            discount_rule=self.discount_rule,
            status=Subscription.Status.CONFIRMED,
            payment_terms_days=15,
            start_date=datetime.date(2026, 10, 1),
        )
        SubscriptionLine.objects.create(
            subscription=self.subscription,
            product=self.product,
            variant=self.variant,
            quantity=2,
            unit_price=Decimal("150.00"),  # 100 + 50
        )
        transition_to_active(self.subscription, start_date=datetime.date(2026, 10, 1))
        # After activation, current_period_start = 2026-10-01, current_period_end = 2026-11-01, next_billing_date = 2026-10-01

    def test_generate_invoice_for_subscription_exact_pricing(self):
        invoice = generate_invoice_for_subscription(
            self.subscription, target_date=datetime.date(2026, 10, 1)
        )
        # Base: 1000.00, Lines: 2x 150 = 300.00. Subtotal: 1300.00
        # Discount: 10% on each line -> 100.00 + 30.00 = 130.00
        # Net: 1170.00
        # Tax 18% on (900) = 162.00, on (270) = 48.60 -> total tax = 210.60
        # Total: 1380.60
        self.assertEqual(invoice.subtotal, Decimal("1300.00"))
        self.assertEqual(invoice.discount_total, Decimal("130.00"))
        self.assertEqual(invoice.net_total, Decimal("1170.00"))
        self.assertEqual(invoice.tax_total, Decimal("210.60"))
        self.assertEqual(invoice.total, Decimal("1380.60"))
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(invoice.lines.count(), 2)

    def test_duplicate_billing_rejected(self):
        generate_invoice_for_subscription(self.subscription, target_date=datetime.date(2026, 10, 1))
        with self.assertRaises(DuplicateBillingError):
            generate_invoice_for_subscription(
                self.subscription, target_date=datetime.date(2026, 10, 1)
            )

    def test_advance_subscription_period_regular_monthly(self):
        advance_subscription_period(self.subscription, target_date=datetime.date(2026, 10, 1))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.current_period_start, datetime.date(2026, 11, 1))
        self.assertEqual(self.subscription.current_period_end, datetime.date(2026, 12, 1))
        self.assertEqual(self.subscription.next_billing_date, datetime.date(2026, 11, 1))
        self.assertEqual(self.subscription.status, Subscription.Status.ACTIVE)

    def test_advance_subscription_period_auto_closes_on_contract_expiry(self):
        self.subscription.expiry_date = datetime.date(2026, 11, 1)
        self.subscription.auto_close_on_expiry = True
        self.subscription.save()

        advance_subscription_period(self.subscription, target_date=datetime.date(2026, 10, 1))
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, Subscription.Status.CLOSED)
        self.assertIsNone(self.subscription.next_billing_date)
        self.assertEqual(self.subscription.close_date, datetime.date(2026, 11, 1))

    def test_run_recurring_billing_end_to_end_and_idempotency(self):
        # Target date is 2026-10-01 (matches next_billing_date)
        record = run_recurring_billing(target_date=datetime.date(2026, 10, 1))
        self.assertTrue(record.success)
        self.assertEqual(record.subscriptions_checked, 1)
        self.assertEqual(record.invoices_created, 1)
        self.assertEqual(record.total_billed_amount, Decimal("1380.60"))

        # Re-running immediately on 2026-10-01 should bill 0 invoices because next_billing_date advanced to 2026-11-01
        second_record = run_recurring_billing(target_date=datetime.date(2026, 10, 1))
        self.assertEqual(second_record.invoices_created, 0)

    def test_run_recurring_billing_skips_paused_and_future_subscriptions(self):
        self.subscription.is_paused = True
        self.subscription.save()
        record = run_recurring_billing(target_date=datetime.date(2026, 10, 1))
        self.assertEqual(record.invoices_created, 0)


class BillingViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin@example.com", "LongPhrase!")
        self.staff = User.objects.create_user(
            "staff@example.com", "LongPhrase!", role=User.Role.STAFF
        )
        self.customer = User.objects.create_user(
            "customer@example.com", "LongPhrase!", role=User.Role.CUSTOMER
        )
        self.other_customer = User.objects.create_user(
            "other@example.com", "LongPhrase!", role=User.Role.CUSTOMER
        )
        self.product = Product.objects.create(
            name="Cloud Server",
            product_type=Product.ProductType.SERVICE,
            sales_price=Decimal("2000.00"),
            cost_price=Decimal("600.00"),
        )
        self.tax_rate = TaxRate.objects.create(name="GST 18%", rate=Decimal("18.00"))
        self.discount_rule = DiscountRule.objects.create(
            name="Early Bird ₹100",
            kind=DiscountRule.Kind.FIXED,
            value=Decimal("100.00"),
            scope=DiscountRule.Scope.SUBSCRIPTION,
        )
        self.invoice = Invoice.objects.create(
            customer=self.customer,
            status=Invoice.Status.CONFIRMED,
            period_start=datetime.date(2026, 10, 1),
            period_end=datetime.date(2026, 11, 1),
            due_date=datetime.date(2026, 10, 15),
            subtotal=Decimal("2000.00"),
            net_total=Decimal("2000.00"),
            total=Decimal("2000.00"),
        )

    # ── Permission Checks ─────────────────────────────────────────────────────

    def test_anonymous_denied_billing_views(self):
        for url in [
            "/billing/taxes/",
            "/billing/discounts/",
            "/billing/invoices/",
            f"/billing/invoices/{self.invoice.pk}/",
            "/billing/runs/",
            "/billing/my-invoices/",
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn(response.status_code, [302, 403])

    def test_customer_denied_staff_billing_views(self):
        self.client.force_login(self.customer)
        for url in [
            "/billing/taxes/",
            "/billing/discounts/",
            "/billing/invoices/",
            "/billing/runs/",
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_customer_scoped_to_own_invoices(self):
        other_invoice = Invoice.objects.create(
            customer=self.other_customer,
            status=Invoice.Status.CONFIRMED,
            due_date=datetime.date(2026, 10, 15),
            total=Decimal("3000.00"),
        )
        self.client.force_login(self.customer)

        # List view shows only self.invoice, not other_invoice
        response = self.client.get("/billing/my-invoices/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.invoice.number)
        self.assertNotContains(response, other_invoice.number)

        # Direct access to other customer's invoice fails
        resp = self.client.get(f"/billing/my-invoices/{other_invoice.pk}/")
        self.assertEqual(resp.status_code, 404)

        resp2 = self.client.get(f"/billing/invoices/{other_invoice.pk}/")
        self.assertEqual(resp2.status_code, 403)

    # ── Staff Operations ──────────────────────────────────────────────────────

    def test_staff_can_view_invoice_list_and_detail(self):
        self.client.force_login(self.staff)
        response = self.client.get("/billing/invoices/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.invoice.number)

        detail_resp = self.client.get(f"/billing/invoices/{self.invoice.pk}/")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, self.invoice.number)

    def test_staff_can_confirm_and_cancel_invoice(self):
        self.client.force_login(self.staff)
        draft_inv = Invoice.objects.create(
            customer=self.customer,
            status=Invoice.Status.DRAFT,
            due_date=datetime.date(2026, 10, 15),
            total=Decimal("500.00"),
        )
        # Confirm
        conf_resp = self.client.post(f"/billing/invoices/{draft_inv.pk}/confirm/")
        self.assertEqual(conf_resp.status_code, 302)
        draft_inv.refresh_from_db()
        self.assertEqual(draft_inv.status, Invoice.Status.CONFIRMED)

        # Cancel
        canc_resp = self.client.post(f"/billing/invoices/{draft_inv.pk}/cancel/")
        self.assertEqual(canc_resp.status_code, 302)
        draft_inv.refresh_from_db()
        self.assertEqual(draft_inv.status, Invoice.Status.CANCELLED)

    def test_print_view_renders_cleanly(self):
        self.client.force_login(self.customer)
        response = self.client.get(f"/billing/invoices/{self.invoice.pk}/print/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.invoice.number)
        self.assertContains(response, "brightloop.")

    def test_staff_can_trigger_billing_run(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            "/billing/runs/execute/",
            {"target_date": "2026-10-31"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BillingRunRecord.objects.filter(run_date="2026-10-31").exists())
