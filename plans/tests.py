from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from catalog.models import Product, ProductVariant

from .models import Plan, QuotationTemplate, QuotationTemplateLine


class PlanModelTests(TestCase):
    def test_all_four_billing_intervals_configurable(self):
        """Specification requires Daily, Weekly, Monthly, and Yearly intervals."""
        for interval in [
            Plan.Interval.DAILY,
            Plan.Interval.WEEKLY,
            Plan.Interval.MONTHLY,
            Plan.Interval.YEARLY,
        ]:
            with self.subTest(interval=interval):
                plan = Plan.objects.create(
                    name=f"Plan {interval}",
                    code=f"plan-{interval.lower()}",
                    interval=interval,
                    price=Decimal("99.00"),
                    min_quantity=1,
                )
                self.assertEqual(plan.interval, interval)
                self.assertEqual(plan.price, Decimal("99.00"))

    def test_database_rejects_negative_price(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Plan.objects.create(
                name="Negative Plan",
                code="neg-plan",
                price=Decimal("-1.00"),
            )

    def test_database_rejects_zero_or_negative_min_quantity(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Plan.objects.create(
                name="Zero Qty Plan",
                code="zero-qty",
                min_quantity=0,
            )

    def test_availability_date_validation(self):
        plan = Plan(
            name="Date Test Plan",
            code="date-test",
            available_from=date(2026, 6, 1),
            available_until=date(2026, 5, 1),  # before available_from!
        )
        with self.assertRaises(ValidationError):
            plan.clean()

    def test_is_available_on_checks(self):
        plan = Plan.objects.create(
            name="Limited Season Plan",
            code="season-plan",
            available_from=date(2026, 6, 1),
            available_until=date(2026, 6, 30),
        )
        self.assertFalse(plan.is_available_on(date(2026, 5, 31)))
        self.assertTrue(plan.is_available_on(date(2026, 6, 1)))
        self.assertTrue(plan.is_available_on(date(2026, 6, 15)))
        self.assertTrue(plan.is_available_on(date(2026, 6, 30)))
        self.assertFalse(plan.is_available_on(date(2026, 7, 1)))

        # Inactive plan is never available
        plan.is_active = False
        plan.save()
        self.assertFalse(plan.is_available_on(date(2026, 6, 15)))

    def test_validate_quantity_enforces_minimum(self):
        plan = Plan.objects.create(
            name="Enterprise Team",
            code="team-enterprise",
            min_quantity=5,
        )
        plan.validate_quantity(5)  # ok
        plan.validate_quantity(10)  # ok
        with self.assertRaises(ValidationError):
            plan.validate_quantity(4)

    def test_lifecycle_policy_flags(self):
        plan = Plan.objects.create(
            name="Strict Annual",
            code="strict-annual",
            interval=Plan.Interval.YEARLY,
            can_pause=False,
            can_early_close=False,
            auto_close_on_expiry=True,
            can_renew=False,
        )
        self.assertFalse(plan.can_pause)
        self.assertFalse(plan.can_early_close)
        self.assertTrue(plan.auto_close_on_expiry)
        self.assertFalse(plan.can_renew)


class QuotationTemplateModelTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            name="Professional Monthly",
            code="pro-monthly",
            interval=Plan.Interval.MONTHLY,
            price=Decimal("1500.00"),
            min_quantity=1,
        )
        self.product = Product.objects.create(
            name="CRM Seat",
            product_type=Product.ProductType.SERVICE,
            sales_price=Decimal("500.00"),
            cost_price=Decimal("100.00"),
        )
        self.other_product = Product.objects.create(
            name="Accounting Addon",
            sales_price=Decimal("200.00"),
            cost_price=Decimal("50.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="CRM Pro Edition",
            price_extra=Decimal("150.00"),
        )

    def test_create_quotation_template_with_lines(self):
        template = QuotationTemplate.objects.create(
            name="Standard Onboarding Quote",
            plan=self.plan,
            validity_days=45,
            notes="30 days payment terms.",
        )
        line = QuotationTemplateLine.objects.create(
            template=template,
            product=self.product,
            variant=self.variant,
            quantity=3,
        )
        self.assertEqual(line.unit_price, Decimal("650.00"))  # 500 + 150
        self.assertEqual(line.line_total, Decimal("1950.00"))  # 650 * 3

    def test_line_variant_must_belong_to_product(self):
        template = QuotationTemplate.objects.create(
            name="Test Template",
            plan=self.plan,
        )
        # Variant belongs to self.product, but line assigns self.other_product
        line = QuotationTemplateLine(
            template=template,
            product=self.other_product,
            variant=self.variant,
            quantity=1,
        )
        with self.assertRaises(ValidationError):
            line.clean()


class PlanAndTemplateViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin@example.com", "LongPhrase!")
        self.staff = User.objects.create_user(
            "staff@example.com", "LongPhrase!", role=User.Role.STAFF
        )
        self.customer = User.objects.create_user(
            "customer@example.com", "LongPhrase!", role=User.Role.CUSTOMER
        )

        self.plan = Plan.objects.create(
            name="Cloud Starter",
            code="cloud-starter",
            interval=Plan.Interval.MONTHLY,
            price=Decimal("999.00"),
            min_quantity=2,
            available_from=date.today() - timedelta(days=5),
            available_until=date.today() + timedelta(days=25),
        )
        self.future_plan = Plan.objects.create(
            name="Future Summer Plan",
            code="summer-plan",
            interval=Plan.Interval.YEARLY,
            price=Decimal("9999.00"),
            available_from=date.today() + timedelta(days=30),
        )

        self.product = Product.objects.create(
            name="User License",
            sales_price=Decimal("100.00"),
            cost_price=Decimal("20.00"),
        )
        self.template = QuotationTemplate.objects.create(
            name="Starter Package Template",
            plan=self.plan,
            validity_days=30,
        )
        QuotationTemplateLine.objects.create(
            template=self.template,
            product=self.product,
            quantity=2,
        )

    # ── Plan View Permissions & Filtering ─────────────────────────────────────

    def test_customer_only_sees_currently_available_plans(self):
        self.client.force_login(self.customer)
        response = self.client.get("/plans/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cloud Starter")
        # Future plan is not yet available; customer should not see it
        self.assertNotContains(response, "Future Summer Plan")

    def test_staff_sees_all_plans_including_future_and_inactive(self):
        self.client.force_login(self.staff)
        response = self.client.get("/plans/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cloud Starter")
        self.assertContains(response, "Future Summer Plan")

    def test_customer_cannot_create_or_edit_plan(self):
        self.client.force_login(self.customer)
        response = self.client.get("/plans/new/")
        self.assertEqual(response.status_code, 403)
        response = self.client.get(f"/plans/{self.plan.pk}/edit/")
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_plan_with_form_validation(self):
        self.client.force_login(self.staff)
        # Invalid date order: available_from > available_until
        response = self.client.post(
            "/plans/new/",
            {
                "name": "Invalid Date Plan",
                "code": "invalid-dates",
                "interval": "MONTHLY",
                "price": "500.00",
                "min_quantity": 1,
                "available_from": "2026-10-15",
                "available_until": "2026-10-01",
                "is_active": "on",
                "can_pause": "on",
                "can_early_close": "on",
                "auto_close_on_expiry": "on",
                "can_renew": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Available until date must be on or after available from date."
        )

        # Valid submission
        response = self.client.post(
            "/plans/new/",
            {
                "name": "Weekly Growth",
                "code": "weekly-growth",
                "interval": "WEEKLY",
                "price": "250.00",
                "min_quantity": 1,
                "is_active": "on",
                "can_pause": "on",
                "can_early_close": "on",
                "auto_close_on_expiry": "on",
                "can_renew": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Plan.objects.filter(code="weekly-growth").exists())

    # ── Quotation Templates Permissions & Preview ─────────────────────────────

    def test_customer_cannot_access_templates(self):
        self.client.force_login(self.customer)
        for url in [
            "/plans/templates/",
            "/plans/templates/new/",
            f"/plans/templates/{self.template.pk}/",
            f"/plans/templates/{self.template.pk}/edit/",
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_staff_can_view_template_detail_with_pricing_preview(self):
        self.client.force_login(self.staff)
        response = self.client.get(f"/plans/templates/{self.template.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Starter Package Template")
        self.assertContains(response, "User License")
        # Plan price: 999.00; 2x License at 100.00 = 200.00; Total = 1199.00
        self.assertContains(response, "1199.00")

    def test_staff_can_add_and_delete_template_line(self):
        self.client.force_login(self.staff)
        addon = Product.objects.create(
            name="Storage Addon", sales_price=Decimal("150.00"), cost_price=Decimal("30.00")
        )

        # Add line
        response = self.client.post(
            f"/plans/templates/{self.template.pk}/lines/new/",
            {"product": str(addon.pk), "quantity": 3},
        )
        self.assertEqual(response.status_code, 302)
        new_line = QuotationTemplateLine.objects.get(template=self.template, product=addon)
        self.assertEqual(new_line.quantity, 3)

        # Delete line
        del_response = self.client.post(
            f"/plans/templates/{self.template.pk}/lines/{new_line.pk}/delete/"
        )
        self.assertEqual(del_response.status_code, 302)
        self.assertFalse(QuotationTemplateLine.objects.filter(pk=new_line.pk).exists())
