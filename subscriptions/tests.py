import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from billing.models import DiscountRule, TaxRate
from catalog.models import Product, ProductVariant
from plans.models import Plan, QuotationTemplate, QuotationTemplateLine
from subscriptions.models import (
    Subscription,
    SubscriptionLine,
    compute_next_period_end,
)
from subscriptions.services import (
    calculate_subscription_pricing,
    close_subscription,
    create_subscription_from_template,
    pause_subscription,
    renew_subscription,
    resume_subscription,
    transition_to_active,
    transition_to_confirmed,
    transition_to_quotation,
)

User = get_user_model()


class SubscriptionModelTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email="cust@example.com",
            password="StrongPassword1!",
            role=User.Role.CUSTOMER,
        )
        self.plan = Plan.objects.create(
            name="Pro Monthly",
            code="pro-monthly",
            interval=Plan.Interval.MONTHLY,
            price=Decimal("100.00"),
            min_quantity=2,
        )
        self.product = Product.objects.create(
            name="Cloud Seat",
            sales_price=Decimal("50.00"),
            cost_price=Decimal("20.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="Priority Support",
            price_extra=Decimal("15.00"),
        )

    def test_auto_generated_number(self):
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
        )
        self.assertTrue(sub.number.startswith("SUB-"))
        self.assertIn(self.customer.email, str(sub))

    def test_period_end_computation_clamped_and_clipped(self):
        # Monthly calculation
        jan31 = datetime.date(2026, 1, 31)
        feb_end = compute_next_period_end(jan31, "MONTHLY")
        self.assertEqual(feb_end, datetime.date(2026, 2, 28))

        # Yearly calculation
        yearly_end = compute_next_period_end(datetime.date(2026, 3, 1), "YEARLY")
        self.assertEqual(yearly_end, datetime.date(2027, 3, 1))

        # Clipped to contractual expiry date
        expiry = datetime.date(2026, 2, 15)
        clipped_end = compute_next_period_end(jan31, "MONTHLY", expiry=expiry)
        self.assertEqual(clipped_end, expiry)

    def test_negative_base_price_rejected_by_db(self):
        sub = Subscription(
            customer=self.customer,
            plan=self.plan,
            base_price=Decimal("-10.00"),
        )
        with self.assertRaises(IntegrityError):
            sub.save()

    def test_negative_payment_terms_rejected_by_db(self):
        sub = Subscription(
            customer=self.customer,
            plan=self.plan,
            payment_terms_days=-5,
        )
        with self.assertRaises(IntegrityError):
            sub.save()

    def test_expiry_before_start_date_rejected_by_db(self):
        sub = Subscription(
            customer=self.customer,
            plan=self.plan,
            start_date=datetime.date(2026, 5, 10),
            expiry_date=datetime.date(2026, 5, 1),
        )
        with self.assertRaises(IntegrityError):
            sub.save()

    def test_line_quantity_min_1_rejected_by_db(self):
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
        )
        line = SubscriptionLine(
            subscription=sub,
            product=self.product,
            quantity=0,
            unit_price=Decimal("50.00"),
        )
        with self.assertRaises(IntegrityError):
            line.save()

    def test_line_variant_must_belong_to_product(self):
        other_product = Product.objects.create(
            name="Other Item",
            sales_price=Decimal("10.00"),
            cost_price=Decimal("4.00"),
        )
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
        )
        line = SubscriptionLine(
            subscription=sub,
            product=other_product,
            variant=self.variant,
            quantity=1,
            unit_price=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            line.clean()


class SubscriptionLifecycleServiceTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email="cust@example.com",
            password="StrongPassword1!",
            role=User.Role.CUSTOMER,
        )
        self.plan = Plan.objects.create(
            name="Team Plan",
            code="team-plan",
            interval=Plan.Interval.MONTHLY,
            price=Decimal("200.00"),
            min_quantity=3,
            can_pause=True,
            can_early_close=True,
            can_renew=True,
        )
        self.product = Product.objects.create(
            name="Seat License",
            sales_price=Decimal("40.00"),
            cost_price=Decimal("15.00"),
        )

    def test_transition_to_quotation_requires_lines_and_min_quantity(self):
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
            status=Subscription.Status.DRAFT,
        )
        with self.assertRaises(ValidationError) as ctx:
            transition_to_quotation(sub)
        self.assertIn("at least one product line", str(ctx.exception))

        SubscriptionLine.objects.create(
            subscription=sub,
            product=self.product,
            quantity=2,
            unit_price=Decimal("40.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            transition_to_quotation(sub)
        self.assertIn("less than plan minimum required quantity", str(ctx.exception))

        line = sub.lines.first()
        line.quantity = 3
        line.save()

        transition_to_quotation(sub, validity_days=15)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.QUOTATION)
        self.assertEqual(sub.quotation_date, timezone.localdate())
        self.assertEqual(
            sub.quotation_valid_until,
            timezone.localdate() + datetime.timedelta(days=15),
        )

    def test_confirm_rejects_expired_quotation(self):
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
            status=Subscription.Status.QUOTATION,
            quotation_date=timezone.localdate() - datetime.timedelta(days=20),
            quotation_valid_until=timezone.localdate() - datetime.timedelta(days=5),
        )
        SubscriptionLine.objects.create(
            subscription=sub,
            product=self.product,
            quantity=3,
            unit_price=Decimal("40.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            transition_to_confirmed(sub)
        self.assertIn("quotation expired", str(ctx.exception).lower())

    def test_full_happy_lifecycle_and_pause_resume(self):
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
            base_price=self.plan.price,
            status=Subscription.Status.DRAFT,
        )
        SubscriptionLine.objects.create(
            subscription=sub,
            product=self.product,
            quantity=3,
            unit_price=Decimal("40.00"),
        )

        # 1. Draft -> Quotation
        transition_to_quotation(sub, validity_days=30)
        self.assertEqual(sub.status, Subscription.Status.QUOTATION)

        # 2. Quotation -> Confirmed
        transition_to_confirmed(sub)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.CONFIRMED)

        # 3. Confirmed -> Active
        start = datetime.date(2026, 11, 1)
        transition_to_active(sub, start_date=start)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.ACTIVE)
        self.assertEqual(sub.current_period_start, start)
        self.assertEqual(sub.current_period_end, datetime.date(2026, 12, 1))
        self.assertEqual(sub.next_billing_date, start)
        self.assertFalse(sub.is_paused)

        # 4. Pause
        pause_subscription(sub, reason="Seasonal holiday break")
        sub.refresh_from_db()
        self.assertTrue(sub.is_paused)
        self.assertEqual(sub.pause_date, timezone.localdate())
        self.assertEqual(sub.pause_reason, "Seasonal holiday break")

        # 5. Resume
        resume_subscription(sub)
        sub.refresh_from_db()
        self.assertFalse(sub.is_paused)
        self.assertIsNone(sub.pause_date)

        # 6. Close
        close_subscription(sub, reason="Customer requested closure")
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.CLOSED)
        self.assertEqual(sub.close_date, timezone.localdate())

    def test_early_close_blocked_if_disallowed(self):
        plan = Plan.objects.create(
            name="Locked Annual",
            code="locked-annual",
            interval=Plan.Interval.YEARLY,
            price=Decimal("1000.00"),
            min_quantity=1,
            can_early_close=False,
        )
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=plan,
            status=Subscription.Status.ACTIVE,
            can_early_close=False,
            start_date=timezone.localdate(),
            expiry_date=timezone.localdate() + datetime.timedelta(days=365),
        )
        SubscriptionLine.objects.create(
            subscription=sub,
            product=self.product,
            quantity=1,
            unit_price=Decimal("40.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            close_subscription(sub)
        self.assertIn("does not allow early closure", str(ctx.exception))

    def test_renewal_extends_contract_expiry(self):
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
            status=Subscription.Status.ACTIVE,
            can_renew=True,
            start_date=datetime.date(2026, 1, 1),
            expiry_date=datetime.date(2026, 12, 31),
        )
        new_expiry = datetime.date(2027, 12, 31)
        renew_subscription(sub, new_expiry_date=new_expiry)
        sub.refresh_from_db()
        self.assertEqual(sub.expiry_date, new_expiry)


class TemplateQuotationAndPricingTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email="cust@example.com",
            password="StrongPassword1!",
            role=User.Role.CUSTOMER,
        )
        self.plan = Plan.objects.create(
            name="Starter Monthly",
            code="starter-monthly",
            interval=Plan.Interval.MONTHLY,
            price=Decimal("100.00"),
            min_quantity=1,
        )
        self.product = Product.objects.create(
            name="Core Platform Seat",
            sales_price=Decimal("50.00"),
            cost_price=Decimal("15.00"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="Gold Tier",
            price_extra=Decimal("20.00"),
        )
        self.tax_rate = TaxRate.objects.create(
            name="GST 18%", rate=Decimal("18.00"), is_active=True
        )
        self.discount_rule = DiscountRule.objects.create(
            name="Welcome 10%",
            kind=DiscountRule.Kind.PERCENTAGE,
            value=Decimal("10.00"),
            scope=DiscountRule.Scope.SUBSCRIPTION,
            is_active=True,
        )

        # Quotation template
        self.template = QuotationTemplate.objects.create(
            name="Gold Startup Pack",
            plan=self.plan,
            validity_days=14,
            notes="Standard introductory pack terms.",
        )
        QuotationTemplateLine.objects.create(
            template=self.template,
            product=self.product,
            variant=self.variant,
            quantity=2,
        )

    def test_create_subscription_from_template(self):
        sub = create_subscription_from_template(
            template=self.template,
            customer=self.customer,
            notes="Custom deal notes",
        )
        self.assertEqual(sub.customer, self.customer)
        self.assertEqual(sub.plan, self.plan)
        self.assertEqual(sub.status, Subscription.Status.QUOTATION)
        self.assertEqual(sub.base_price, Decimal("100.00"))
        self.assertEqual(sub.notes, "Custom deal notes")
        self.assertEqual(
            sub.quotation_valid_until,
            timezone.localdate() + datetime.timedelta(days=14),
        )

        lines = sub.lines.all()
        self.assertEqual(lines.count(), 1)
        line = lines.first()
        self.assertEqual(line.product, self.product)
        self.assertEqual(line.variant, self.variant)
        self.assertEqual(line.quantity, 2)
        self.assertEqual(line.unit_price, Decimal("70.00"))

    def test_calculate_subscription_pricing_with_taxes_and_discounts(self):
        sub = create_subscription_from_template(
            template=self.template,
            customer=self.customer,
        )
        sub.tax_rate = self.tax_rate
        sub.discount_rule = self.discount_rule
        sub.save()

        pricing = calculate_subscription_pricing(sub)
        self.assertIsNotNone(pricing)
        self.assertEqual(pricing.discount, Decimal("24.00"))
        self.assertEqual(pricing.net, Decimal("216.00"))
        self.assertEqual(pricing.tax, Decimal("38.88"))
        self.assertEqual(pricing.total, Decimal("254.88"))


class SubscriptionViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            email="staff@example.com",
            password="StrongPassword1!",
            role=User.Role.STAFF,
        )
        self.customer1 = User.objects.create_user(
            email="cust1@example.com",
            password="StrongPassword1!",
            role=User.Role.CUSTOMER,
        )
        self.customer2 = User.objects.create_user(
            email="cust2@example.com",
            password="StrongPassword1!",
            role=User.Role.CUSTOMER,
        )
        self.plan = Plan.objects.create(
            name="Business Monthly",
            code="business-monthly",
            interval=Plan.Interval.MONTHLY,
            price=Decimal("150.00"),
            min_quantity=1,
        )
        self.product = Product.objects.create(
            name="User License",
            sales_price=Decimal("30.00"),
            cost_price=Decimal("10.00"),
        )
        self.sub1 = Subscription.objects.create(
            customer=self.customer1,
            plan=self.plan,
            base_price=self.plan.price,
            status=Subscription.Status.QUOTATION,
            quotation_date=timezone.localdate(),
            quotation_valid_until=timezone.localdate() + datetime.timedelta(days=10),
        )
        SubscriptionLine.objects.create(
            subscription=self.sub1,
            product=self.product,
            quantity=1,
            unit_price=Decimal("30.00"),
        )

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse("subscriptions:subscription_list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_customer_scoped_visibility(self):
        self.client.force_login(self.customer2)
        resp = self.client.get(reverse("subscriptions:subscription_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, self.sub1.number)

        detail_resp = self.client.get(
            reverse("subscriptions:subscription_detail", kwargs={"pk": self.sub1.pk})
        )
        self.assertEqual(detail_resp.status_code, 404)

        self.client.force_login(self.customer1)
        resp1 = self.client.get(reverse("subscriptions:subscription_list"))
        self.assertEqual(resp1.status_code, 200)
        self.assertContains(resp1, self.sub1.number)

    def test_customer_can_confirm_own_valid_quotation(self):
        self.client.force_login(self.customer1)
        resp = self.client.post(
            reverse(
                "subscriptions:subscription_transition",
                kwargs={"pk": self.sub1.pk, "action": "confirm"},
            ),
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.sub1.refresh_from_db()
        self.assertEqual(self.sub1.status, Subscription.Status.CONFIRMED)

    def test_staff_can_create_and_manage_subscription_and_lines(self):
        self.client.force_login(self.staff_user)

        # 1. Create subscription draft
        create_resp = self.client.post(
            reverse("subscriptions:subscription_create"),
            {
                "customer": str(self.customer2.pk),
                "plan": str(self.plan.pk),
                "base_price": "150.00",
                "payment_terms_days": "15",
                "can_pause": "on",
                "can_early_close": "on",
                "can_renew": "on",
                "auto_close_on_expiry": "on",
            },
            follow=True,
        )
        self.assertEqual(create_resp.status_code, 200)
        sub2 = Subscription.objects.get(customer=self.customer2)
        self.assertEqual(sub2.status, Subscription.Status.DRAFT)

        # 2. Add line
        add_line_resp = self.client.post(
            reverse("subscriptions:subscription_line_add", kwargs={"pk": sub2.pk}),
            {
                "product": str(self.product.pk),
                "quantity": 2,
                "unit_price": "30.00",
            },
            follow=True,
        )
        self.assertEqual(add_line_resp.status_code, 200)
        self.assertEqual(sub2.lines.count(), 1)

        # 3. Issue quotation
        quote_resp = self.client.post(
            reverse(
                "subscriptions:subscription_transition",
                kwargs={"pk": sub2.pk, "action": "send_quote"},
            ),
            {"validity_days": "20"},
            follow=True,
        )
        self.assertEqual(quote_resp.status_code, 200)
        sub2.refresh_from_db()
        self.assertEqual(sub2.status, Subscription.Status.QUOTATION)

        # 4. Confirm
        confirm_resp = self.client.post(
            reverse(
                "subscriptions:subscription_transition",
                kwargs={"pk": sub2.pk, "action": "confirm"},
            ),
            follow=True,
        )
        self.assertEqual(confirm_resp.status_code, 200)
        sub2.refresh_from_db()
        self.assertEqual(sub2.status, Subscription.Status.CONFIRMED)

        # 5. Activate
        activate_resp = self.client.post(
            reverse(
                "subscriptions:subscription_transition",
                kwargs={"pk": sub2.pk, "action": "activate"},
            ),
            {"start_date": "2026-11-01"},
            follow=True,
        )
        self.assertEqual(activate_resp.status_code, 200)
        sub2.refresh_from_db()
        self.assertEqual(sub2.status, Subscription.Status.ACTIVE)
        self.assertEqual(sub2.current_period_start, datetime.date(2026, 11, 1))

    def test_customer_can_pause_and_resume_own_subscription(self):
        self.sub1.status = Subscription.Status.ACTIVE
        self.sub1.can_pause = True
        self.sub1.save()

        self.client.force_login(self.customer1)
        # Pause
        resp = self.client.post(
            reverse(
                "subscriptions:subscription_transition",
                kwargs={"pk": self.sub1.pk, "action": "pause"},
            ),
            {"reason": "Vacation pause"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.sub1.refresh_from_db()
        self.assertTrue(self.sub1.is_paused)
        self.assertEqual(self.sub1.pause_reason, "Vacation pause")

        # Resume
        resp = self.client.post(
            reverse(
                "subscriptions:subscription_transition",
                kwargs={"pk": self.sub1.pk, "action": "resume"},
            ),
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.sub1.refresh_from_db()
        self.assertFalse(self.sub1.is_paused)

    def test_customer_can_cancel_subscription_when_permitted(self):
        self.sub1.status = Subscription.Status.ACTIVE
        self.sub1.can_early_close = True
        self.sub1.save()

        self.client.force_login(self.customer1)
        resp = self.client.post(
            reverse(
                "subscriptions:subscription_transition",
                kwargs={"pk": self.sub1.pk, "action": "close"},
            ),
            {"reason": "Moving out of region"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.sub1.refresh_from_db()
        self.assertEqual(self.sub1.status, Subscription.Status.CLOSED)
        self.assertEqual(self.sub1.close_reason, "Moving out of region")

    def test_customer_cannot_cancel_subscription_when_early_close_disallowed(self):
        self.sub1.status = Subscription.Status.ACTIVE
        self.sub1.can_early_close = False
        self.sub1.start_date = timezone.localdate()
        self.sub1.expiry_date = timezone.localdate() + datetime.timedelta(days=180)
        self.sub1.save()

        self.client.force_login(self.customer1)
        resp = self.client.post(
            reverse(
                "subscriptions:subscription_transition",
                kwargs={"pk": self.sub1.pk, "action": "close"},
            ),
            {"reason": "Trying to cancel locked term"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.sub1.refresh_from_db()
        self.assertEqual(self.sub1.status, Subscription.Status.ACTIVE)
        self.assertContains(resp, "does not permit early cancellation")

    def test_customer_can_update_line_quantity(self):
        self.sub1.status = Subscription.Status.ACTIVE
        self.sub1.save()
        line = self.sub1.lines.first()

        self.client.force_login(self.customer1)
        resp = self.client.post(
            reverse(
                "subscriptions:subscription_line_update_quantity",
                kwargs={"pk": self.sub1.pk, "line_pk": line.pk},
            ),
            {"quantity": 4},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        line.refresh_from_db()
        self.assertEqual(line.quantity, 4)

    def test_customer_update_quantity_below_plan_min_rejected(self):
        self.plan.min_quantity = 3
        self.plan.save()
        self.sub1.status = Subscription.Status.ACTIVE
        self.sub1.save()
        line = self.sub1.lines.first()

        self.client.force_login(self.customer1)
        resp = self.client.post(
            reverse(
                "subscriptions:subscription_line_update_quantity",
                kwargs={"pk": self.sub1.pk, "line_pk": line.pk},
            ),
            {"quantity": 2},  # 2 < min_quantity 3
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        line.refresh_from_db()
        self.assertEqual(line.quantity, 1)  # unchanged
        self.assertContains(resp, "minimum required seats")

    def test_customer_cannot_modify_other_customer_subscription(self):
        self.client.force_login(self.customer2)
        # Attempt to pause customer 1's subscription
        resp = self.client.post(
            reverse(
                "subscriptions:subscription_transition",
                kwargs={"pk": self.sub1.pk, "action": "pause"},
            ),
            follow=True,
        )
        self.assertEqual(resp.status_code, 404)

        # Attempt to update line quantity on customer 1's subscription
        line = self.sub1.lines.first()
        resp_line = self.client.post(
            reverse(
                "subscriptions:subscription_line_update_quantity",
                kwargs={"pk": self.sub1.pk, "line_pk": line.pk},
            ),
            {"quantity": 10},
            follow=True,
        )
        self.assertEqual(resp_line.status_code, 404)

    def test_linked_invoices_rendered_in_subscription_detail(self):
        from billing.models import Invoice

        inv = Invoice.objects.create(
            customer=self.customer1,
            subscription=self.sub1,
            number="INV-202610-0999",
            period_start=datetime.date(2026, 10, 1),
            period_end=datetime.date(2026, 11, 1),
            issue_date=datetime.date(2026, 10, 1),
            due_date=datetime.date(2026, 10, 16),
            subtotal=Decimal("180.00"),
            total=Decimal("180.00"),
            status=Invoice.Status.CONFIRMED,
        )

        self.client.force_login(self.customer1)
        resp = self.client.get(
            reverse("subscriptions:subscription_detail", kwargs={"pk": self.sub1.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "INV-202610-0999")
        self.assertContains(resp, "₹180.00")
        self.assertContains(resp, reverse("billing:customer_invoice_detail", kwargs={"pk": inv.pk}))
