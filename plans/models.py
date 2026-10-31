import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Plan(models.Model):
    class Interval(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.SlugField(
        max_length=64, unique=True, help_text="Unique identifier, e.g. 'starter-monthly'."
    )
    interval = models.CharField(max_length=10, choices=Interval.choices, default=Interval.MONTHLY)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Recurring base plan fee per billing cycle in INR.",
    )
    min_quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Minimum seats / units required for subscriptions under this plan.",
    )
    available_from = models.DateField(
        null=True,
        blank=True,
        help_text="First date this plan can be offered (inclusive). Leave blank for immediate.",
    )
    available_until = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this plan can be offered (inclusive). Leave blank for open-ended.",
    )

    # Configurable lifecycle behavior
    can_pause = models.BooleanField(
        default=True,
        help_text="Whether subscribers on this plan are permitted to pause service.",
    )
    can_early_close = models.BooleanField(
        default=True,
        help_text="Whether subscribers can terminate their subscription before the end of the term.",
    )
    auto_close_on_expiry = models.BooleanField(
        default=True,
        help_text="Whether the subscription automatically transitions to CLOSED on expiry date.",
    )
    can_renew = models.BooleanField(
        default=True,
        help_text="Whether the subscription can be explicitly renewed past its initial term.",
    )

    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=Decimal("0.00")),
                name="plans_plan_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(min_quantity__gte=1),
                name="plans_plan_min_quantity_positive",
            ),
        ]

    def clean(self):
        super().clean()
        if self.available_from and self.available_until:
            if self.available_from > self.available_until:
                raise ValidationError(
                    {
                        "available_until": "Available until date must be on or after available from date."
                    }
                )

    def is_available_on(self, target_date=None) -> bool:
        """Return True if this plan is active and available on target_date (defaults to today)."""
        if not self.is_active:
            return False
        date = target_date or timezone.localdate()
        if self.available_from and date < self.available_from:
            return False
        if self.available_until and date > self.available_until:
            return False
        return True

    def validate_quantity(self, quantity: int):
        """Validate whether the given quantity satisfies the plan's minimum requirement."""
        if quantity < self.min_quantity:
            raise ValidationError(
                f"Plan '{self.name}' requires a minimum of {self.min_quantity} unit(s) (provided {quantity})."
            )

    def __str__(self):
        return f"{self.name} ({self.get_interval_display()}) - ₹{self.price}"


class QuotationTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="quotation_templates",
    )
    validity_days = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Default number of days a quotation generated from this template remains valid.",
    )
    notes = models.TextField(
        blank=True, help_text="Terms or instructions automatically included in quotes."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} [{self.plan.name}]"


class QuotationTemplateLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        QuotationTemplate,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="template_lines",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="template_lines",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        ordering = ["template", "product"]

    def clean(self):
        super().clean()
        if self.variant and self.variant.product_id != self.product_id:
            raise ValidationError(
                {
                    "variant": f"Variant '{self.variant.name}' does not belong to product '{self.product.name}'."
                }
            )

    @property
    def unit_price(self) -> Decimal:
        if self.variant:
            return self.variant.effective_sales_price
        return self.product.sales_price

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity

    def __str__(self):
        label = self.variant.name if self.variant else self.product.name
        return f"{self.quantity}x {label} @ ₹{self.unit_price}"
