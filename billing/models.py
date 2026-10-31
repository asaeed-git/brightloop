import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


def generate_invoice_number() -> str:
    now = timezone.now()
    prefix = f"INV-{now.strftime('%Y%m')}"
    last = Invoice.objects.filter(number__startswith=prefix).order_by("-number").first()
    if last and last.number:
        try:
            seq = int(last.number.split("-")[-1]) + 1
        except ValueError, IndexError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}-{seq:04d}"


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


class Invoice(models.Model):
    """An immutable, authoritative billing statement issued to a customer.

    Invoices represent charges for a discrete billing period [period_start, period_end).
    The line items store frozen historical amounts so subsequent catalog edits never
    mutate issued invoices. Unique constraint on (subscription, period_start)
    strictly guards against duplicate cycle billing.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        default=generate_invoice_number,
        help_text="Unique business reference number, e.g. INV-202610-0001",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices",
        help_text="Customer billed on this invoice.",
    )
    subscription = models.ForeignKey(
        "subscriptions.Subscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
        help_text="Originating subscription, if generated by the recurring billing worker.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED,
        db_index=True,
    )
    period_start = models.DateField(
        null=True,
        blank=True,
        help_text="Start of billing period (inclusive).",
    )
    period_end = models.DateField(
        null=True,
        blank=True,
        help_text="End of billing period (exclusive).",
    )
    issue_date = models.DateField(
        default=timezone.localdate,
        db_index=True,
    )
    due_date = models.DateField(
        db_index=True,
        help_text="Payment due date (issue_date + payment terms).",
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when final payment settled the balance.",
    )

    # Immutable Financial Snapshots in INR
    currency = models.CharField(max_length=3, default="INR")
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Gross total before discounts and taxes.",
    )
    discount_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total allocated discount.",
    )
    net_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Taxable net amount (subtotal - discount_total).",
    )
    tax_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total tax calculated across lines.",
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Final amount payable (net_total + tax_total).",
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total payments settled against this invoice.",
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["status", "due_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=Decimal("0.00")),
                name="billing_invoice_subtotal_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(discount_total__gte=Decimal("0.00")),
                name="billing_invoice_discount_total_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(net_total__gte=Decimal("0.00")),
                name="billing_invoice_net_total_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(tax_total__gte=Decimal("0.00")),
                name="billing_invoice_tax_total_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=Decimal("0.00")),
                name="billing_invoice_total_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(amount_paid__gte=Decimal("0.00")),
                name="billing_invoice_amount_paid_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(amount_paid__lte=models.F("total")),
                name="billing_invoice_amount_paid_lte_total",
            ),
            # Critical Anti-Duplication: prevent duplicate billing of the same period for a subscription
            models.UniqueConstraint(
                fields=["subscription", "period_start"],
                condition=models.Q(subscription__isnull=False, period_start__isnull=False),
                name="billing_invoice_subscription_period_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number} ({self.customer.email} - ₹{self.total})"

    @property
    def amount_due(self) -> Decimal:
        return max(Decimal("0.00"), self.total - self.amount_paid)

    @property
    def is_overdue(self) -> bool:
        if self.status == self.Status.CONFIRMED and self.amount_due > Decimal("0.00"):
            return self.due_date < timezone.localdate()
        return False


class InvoiceLine(models.Model):
    """Immutable snapshot line item on an issued invoice."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    description = models.CharField(
        max_length=255,
        help_text="Snapshot line item description (e.g. Plan base fee or product variant).",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Frozen unit price at invoicing time.",
    )
    gross = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    net = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount_rule = models.ForeignKey(
        DiscountRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="billing_invoiceline_quantity_min_1",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=Decimal("0.00")),
                name="billing_invoiceline_unit_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(gross__gte=Decimal("0.00")),
                name="billing_invoiceline_gross_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(discount__gte=Decimal("0.00")),
                name="billing_invoiceline_discount_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(net__gte=Decimal("0.00")),
                name="billing_invoiceline_net_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(tax__gte=Decimal("0.00")),
                name="billing_invoiceline_tax_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=Decimal("0.00")),
                name="billing_invoiceline_total_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity}x {self.description} = ₹{self.total}"


class BillingRunRecord(models.Model):
    """Historical audit record of a recurring billing worker execution."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run_date = models.DateField(
        default=timezone.localdate,
        db_index=True,
        help_text="Target date for which recurring billing was executed.",
    )
    executed_at = models.DateTimeField(auto_now_add=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Staff or admin user who triggered the run (null if automated worker).",
    )
    subscriptions_checked = models.PositiveIntegerField(default=0)
    invoices_created = models.PositiveIntegerField(default=0)
    total_billed_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    success = models.BooleanField(default=True)
    log_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-executed_at"]

    def __str__(self) -> str:
        status_str = "Success" if self.success else "Failed"
        return f"Run on {self.run_date} ({status_str}: {self.invoices_created} invoices, ₹{self.total_billed_amount})"
