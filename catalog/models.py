import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    class ProductType(models.TextChoices):
        SERVICE = "SERVICE", "Service"
        GOODS = "GOODS", "Consumable / Goods"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.SERVICE,
    )
    sales_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Standard sales price excluding tax.",
    )
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Internal unit cost; confidential to staff and admin.",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive products cannot be selected in new quotations or subscriptions.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(sales_price__gte=Decimal("0.00")),
                name="catalog_product_sales_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(cost_price__gte=Decimal("0.00")),
                name="catalog_product_cost_price_non_negative",
            ),
        ]

    def clean(self):
        super().clean()
        if self.pk and self.sales_price is not None:
            for variant in self.variants.all():
                if self.sales_price + variant.price_extra < Decimal("0.00"):
                    raise ValidationError(
                        {
                            "sales_price": (
                                f"Lowering sales price to ₹{self.sales_price} would make variant "
                                f"'{variant.name}' effective price negative."
                            )
                        }
                    )

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(
        max_length=120,
        help_text="Variant label, e.g. 'Pro', 'Enterprise', '560 Edition'.",
    )
    attribute_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Attribute dimension, e.g. 'Edition', 'Storage'.",
    )
    attribute_value = models.CharField(
        max_length=100,
        blank=True,
        help_text="Attribute value, e.g. 'Enterprise', '100GB'.",
    )
    price_extra = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Price adjustment added to the base product sales price.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive variants cannot be selected in new quotations.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "name"],
                name="catalog_variant_product_name_unique",
            ),
        ]

    def clean(self):
        super().clean()
        if hasattr(self, "product") and self.product_id:
            if self.product.sales_price + (self.price_extra or Decimal("0.00")) < Decimal("0.00"):
                raise ValidationError(
                    {
                        "price_extra": "Effective sales price (base product price + variant adjustment) cannot be negative."
                    }
                )

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def effective_sales_price(self) -> Decimal:
        """Total price for this variant: product sales_price + price_extra."""
        return self.product.sales_price + self.price_extra
