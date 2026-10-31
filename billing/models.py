import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TaxRate(models.Model):
    """A named tax rate applied per charge line during invoicing.

    Staff and admin create and manage rates; the calculator receives the rate
    Decimal and applies it per charge line. INR only; two decimal places.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Display name, e.g. 'GST 18%' or 'VAT 5%'.",
    )
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text="Tax percentage, 0.00–100.00. Applied per line after discount.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive rates cannot be selected for new plans or product variants.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rate__gte=Decimal("0.00")),
                name="billing_taxrate_rate_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(rate__lte=Decimal("100.00")),
                name="billing_taxrate_rate_max_100",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class DiscountRule(models.Model):
    """A configurable discount rule applied to eligible charges at invoicing time.

    Kind FIXED: a fixed INR amount distributed across eligible charges using
    largest-remainder allocation (see pricing.services). Kind PERCENTAGE: applied
    per eligible charge line, rounded half-up. At most one rule per charge is
    selected by the billing service; rules do not stack on the same charge.

    Scope SUBSCRIPTION: the rule is eligible across the plan fee and all product
    lines in the invoice. Scope PRODUCT: the rule is eligible only for charges
    whose product_id matches this rule's product.

    The billing service validates dates, thresholds, and usage availability before
    selecting a rule. This model stores configuration only; usage reservation is
    handled transactionally by the billing service (B3).
    """

    class Kind(models.TextChoices):
        FIXED = "FIXED", "Fixed amount (₹)"
        PERCENTAGE = "PERCENTAGE", "Percentage (%)"

    class Scope(models.TextChoices):
        SUBSCRIPTION = "SUBSCRIPTION", "Whole subscription (base fee + all lines)"
        PRODUCT = "PRODUCT", "Specific product lines only"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Human-readable rule label.")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="INR amount for FIXED rules; percentage (0.01–100.00) for PERCENTAGE rules.",
    )
    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
        default=Scope.SUBSCRIPTION,
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="discount_rules",
        help_text="Required when scope is PRODUCT. Leave blank for SUBSCRIPTION scope.",
    )
    min_eligible_gross = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=(
            "Minimum pre-discount, pre-tax eligible gross (INR) required for this rule "
            "to apply. Leave blank for no minimum threshold."
        ),
    )
    valid_from = models.DateField(
        null=True,
        blank=True,
        help_text="Rule is eligible on or after this date (inclusive). Leave blank for no start restriction.",
    )
    valid_until = models.DateField(
        null=True,
        blank=True,
        help_text="Rule is eligible on or before this date (inclusive). Leave blank for no end restriction.",
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Maximum number of invoice-level reservations allowed across all customers. "
            "Leave blank for unlimited use."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive rules cannot be selected for new invoices.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(value__gt=Decimal("0.00")),
                name="billing_discountrule_value_positive",
            ),
            # PRODUCT scope requires a product FK
            models.CheckConstraint(
                condition=~models.Q(scope="PRODUCT") | models.Q(product__isnull=False),
                name="billing_discountrule_product_scope_requires_product",
            ),
            # SUBSCRIPTION scope must not carry a product FK
            models.CheckConstraint(
                condition=~models.Q(scope="SUBSCRIPTION") | models.Q(product__isnull=True),
                name="billing_discountrule_subscription_scope_no_product",
            ),
            # Date range must be coherent when both ends are supplied
            models.CheckConstraint(
                condition=models.Q(valid_from__isnull=True)
                | models.Q(valid_until__isnull=True)
                | models.Q(valid_until__gte=models.F("valid_from")),
                name="billing_discountrule_valid_date_range",
            ),
            models.CheckConstraint(
                condition=models.Q(min_eligible_gross__isnull=True)
                | models.Q(min_eligible_gross__gte=Decimal("0.00")),
                name="billing_discountrule_min_eligible_gross_non_negative",
            ),
        ]

    def __str__(self):
        kind_label = "₹" if self.kind == self.Kind.FIXED else "%"
        return f"{self.name} ({kind_label}{self.value})"
