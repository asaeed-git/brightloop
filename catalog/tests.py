from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User

from .models import Product, ProductVariant


class CatalogModelTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Cloud Storage",
            product_type=Product.ProductType.SERVICE,
            sales_price=Decimal("1200.00"),
            cost_price=Decimal("450.00"),
            notes="Secure distributed object storage.",
        )

    def test_product_creation(self):
        self.assertEqual(self.product.name, "Cloud Storage")
        self.assertEqual(self.product.sales_price, Decimal("1200.00"))
        self.assertEqual(self.product.cost_price, Decimal("450.00"))
        self.assertTrue(self.product.is_active)

    def test_variant_with_560_price_adjustment_from_specification(self):
        """
        The project specification explicitly requires demonstrating a product
        with a priced variant that adds 560 to the base price.
        """
        variant = ProductVariant.objects.create(
            product=self.product,
            name="Pro Plan with Dedicated IP",
            attribute_name="Add-on",
            attribute_value="Dedicated IP",
            price_extra=Decimal("560.00"),
        )
        self.assertEqual(variant.price_extra, Decimal("560.00"))
        # Base 1200.00 + 560.00 = 1760.00
        self.assertEqual(variant.effective_sales_price, Decimal("1760.00"))

    def test_database_rejects_negative_sales_price(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.create(
                name="Negative Product",
                product_type=Product.ProductType.SERVICE,
                sales_price=Decimal("-10.00"),
                cost_price=Decimal("5.00"),
            )

    def test_database_rejects_negative_cost_price(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.create(
                name="Negative Cost",
                product_type=Product.ProductType.SERVICE,
                sales_price=Decimal("100.00"),
                cost_price=Decimal("-50.00"),
            )

    def test_variant_name_unique_per_product(self):
        ProductVariant.objects.create(
            product=self.product,
            name="Standard",
            price_extra=Decimal("0.00"),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductVariant.objects.create(
                product=self.product,
                name="Standard",
                price_extra=Decimal("50.00"),
            )


class CatalogViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin@example.com", "LongPhrase!")
        self.staff = User.objects.create_user(
            "staff@example.com", "LongPhrase!", role=User.Role.STAFF
        )
        self.customer = User.objects.create_user(
            "customer@example.com", "LongPhrase!", role=User.Role.CUSTOMER
        )
        self.product = Product.objects.create(
            name="Enterprise CRM",
            product_type=Product.ProductType.SERVICE,
            sales_price=Decimal("5000.00"),
            cost_price=Decimal("1200.00"),
            notes="Full-suite customer relationship platform.",
        )
        self.variant_560 = ProductVariant.objects.create(
            product=self.product,
            name="Enterprise Plus (+560)",
            attribute_name="Tier",
            attribute_value="Plus",
            price_extra=Decimal("560.00"),
        )

    # ── Confidentiality: Cost price must never leak to customers ──────────────

    def test_customer_view_excludes_cost_price_on_list(self):
        self.client.force_login(self.customer)
        response = self.client.get("/catalog/products/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enterprise CRM")
        self.assertContains(response, "5000.00")
        # Cost price must NOT appear in HTML for customer
        self.assertNotContains(response, "1200.00")
        self.assertNotContains(response, "Cost Price")

    def test_customer_view_excludes_cost_price_on_detail(self):
        self.client.force_login(self.customer)
        response = self.client.get(f"/catalog/products/{self.product.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enterprise CRM")
        self.assertContains(response, "5000.00")
        self.assertContains(response, "560.00")
        self.assertContains(response, "5560.00")
        # Cost price must NOT appear in HTML or product data for customer
        self.assertNotContains(response, "1200.00")
        self.assertNotIn("cost_price", response.context["product"])

    def test_anonymous_view_excludes_cost_price(self):
        response = self.client.get(f"/catalog/products/{self.product.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "1200.00")
        self.assertNotIn("cost_price", response.context["product"])

    def test_staff_and_admin_see_cost_price(self):
        for user in [self.staff, self.admin]:
            with self.subTest(user=user.email):
                self.client.force_login(user)
                response = self.client.get(f"/catalog/products/{self.product.pk}/")
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "1200.00")
                self.assertEqual(response.context["product"]["cost_price"], Decimal("1200.00"))

    # ── Role Guards on Mutations ──────────────────────────────────────────────

    def test_customer_cannot_create_or_edit_products(self):
        self.client.force_login(self.customer)
        for url in [
            "/catalog/products/new/",
            f"/catalog/products/{self.product.pk}/edit/",
            f"/catalog/products/{self.product.pk}/variants/new/",
            f"/catalog/variants/{self.variant_560.pk}/edit/",
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_staff_can_create_product(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            "/catalog/products/new/",
            {
                "name": "Consulting Package",
                "product_type": Product.ProductType.SERVICE,
                "sales_price": "2500.00",
                "cost_price": "800.00",
                "notes": "Onsite implementation.",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(name="Consulting Package").exists())

    def test_staff_can_create_variant_with_560(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            f"/catalog/products/{self.product.pk}/variants/new/",
            {
                "name": "Add-on Support (+560)",
                "attribute_name": "Support",
                "attribute_value": "24/7 Priority",
                "price_extra": "560.00",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        variant = ProductVariant.objects.get(name="Add-on Support (+560)")
        self.assertEqual(variant.price_extra, Decimal("560.00"))
        self.assertEqual(variant.effective_sales_price, Decimal("5560.00"))

    # ── Customer Management Views ─────────────────────────────────────────────

    def test_customer_cannot_access_customer_list_or_detail(self):
        self.client.force_login(self.customer)
        response = self.client.get("/catalog/customers/")
        self.assertEqual(response.status_code, 403)
        response = self.client.get(f"/catalog/customers/{self.customer.pk}/")
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_customers(self):
        self.client.force_login(self.staff)
        response = self.client.get("/catalog/customers/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.customer.email)

        response = self.client.get(f"/catalog/customers/{self.customer.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.customer.email)
