import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from catalog.models import Product

from .forms import DiscountRuleForm, TaxRateForm
from .models import DiscountRule, TaxRate


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


class BillingViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin@example.com", "LongPhrase!")
        self.staff = User.objects.create_user(
            "staff@example.com", "LongPhrase!", role=User.Role.STAFF
        )
        self.customer = User.objects.create_user(
            "customer@example.com", "LongPhrase!", role=User.Role.CUSTOMER
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

    # ── Permission Checks ─────────────────────────────────────────────────────

    def test_anonymous_and_customer_denied_tax_views(self):
        urls = [
            "/billing/taxes/",
            "/billing/taxes/new/",
            f"/billing/taxes/{self.tax_rate.pk}/edit/",
        ]
        for url in urls:
            # Anonymous
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
            # Customer
            self.client.force_login(self.customer)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    def test_anonymous_and_customer_denied_discount_views(self):
        urls = [
            "/billing/discounts/",
            "/billing/discounts/new/",
            f"/billing/discounts/{self.discount_rule.pk}/edit/",
        ]
        for url in urls:
            # Anonymous
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
            # Customer
            self.client.force_login(self.customer)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    # ── Tax Rate Views ────────────────────────────────────────────────────────

    def test_staff_can_view_tax_list(self):
        self.client.force_login(self.staff)
        response = self.client.get("/billing/taxes/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GST 18%")
        self.assertContains(response, "18.00%")

    def test_staff_can_create_tax_rate(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            "/billing/taxes/new/",
            {"name": "VAT 5%", "rate": "5.00", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TaxRate.objects.filter(name="VAT 5%").exists())

    def test_staff_can_edit_tax_rate(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            f"/billing/taxes/{self.tax_rate.pk}/edit/",
            {"name": "GST 18% Updated", "rate": "18.00"},
        )
        self.assertEqual(response.status_code, 302)
        self.tax_rate.refresh_from_db()
        self.assertEqual(self.tax_rate.name, "GST 18% Updated")
        self.assertFalse(self.tax_rate.is_active)

    # ── Discount Rule Views ───────────────────────────────────────────────────

    def test_staff_can_view_discount_list(self):
        self.client.force_login(self.staff)
        response = self.client.get("/billing/discounts/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Early Bird ₹100")

    def test_staff_can_create_fixed_discount_rule(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            "/billing/discounts/new/",
            {
                "name": "Flat ₹500",
                "kind": DiscountRule.Kind.FIXED,
                "value": "500.00",
                "scope": DiscountRule.Scope.SUBSCRIPTION,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(DiscountRule.objects.filter(name="Flat ₹500").exists())

    def test_staff_can_create_product_percentage_discount_rule(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            "/billing/discounts/new/",
            {
                "name": "20% Server Discount",
                "kind": DiscountRule.Kind.PERCENTAGE,
                "value": "20.00",
                "scope": DiscountRule.Scope.PRODUCT,
                "product": str(self.product.pk),
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        rule = DiscountRule.objects.get(name="20% Server Discount")
        self.assertEqual(rule.product, self.product)

    def test_staff_can_edit_discount_rule(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            f"/billing/discounts/{self.discount_rule.pk}/edit/",
            {
                "name": "Early Bird ₹150",
                "kind": DiscountRule.Kind.FIXED,
                "value": "150.00",
                "scope": DiscountRule.Scope.SUBSCRIPTION,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.discount_rule.refresh_from_db()
        self.assertEqual(self.discount_rule.name, "Early Bird ₹150")
        self.assertEqual(self.discount_rule.value, Decimal("150.00"))
        self.assertFalse(self.discount_rule.is_active)
