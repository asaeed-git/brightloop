import calendar
import datetime
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def generate_subscription_number() -> str:
    now = timezone.now()
    prefix = f"SUB-{now.strftime('%Y%m')}"
    last = Subscription.objects.filter(number__startswith=prefix).order_by("-number").first()
    if last and last.number:
        try:
            seq = int(last.number.split("-")[-1]) + 1
        except ValueError, IndexError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}-{seq:04d}"


def compute_next_period_end(
    start: datetime.date, interval: str, expiry: datetime.date | None = None
) -> datetime.date:
    if interval == "DAILY":
        end = start + datetime.timedelta(days=1)
    elif interval == "WEEKLY":
        end = start + datetime.timedelta(days=7)
    elif interval == "MONTHLY":
        year = start.year + (start.month // 12)
        month = (start.month % 12) + 1
        max_day = calendar.monthrange(year, month)[1]
        day = min(start.day, max_day)
        end = datetime.date(year, month, day)
    elif interval == "YEARLY":
        year = start.year + 1
        max_day = calendar.monthrange(year, start.month)[1]
        day = min(start.day, max_day)
        end = datetime.date(year, start.month, day)
    else:
        raise ValueError(f"Unknown billing interval: {interval}")

    if expiry and end > expiry:
        end = expiry
    return end


class Subscription(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        QUOTATION = "QUOTATION", "Quotation"
        CONFIRMED = "CONFIRMED", "Confirmed"
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        default=generate_subscription_number,
        help_text="Unique business reference number, e.g. SUB-202610-0001",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        help_text="Customer user account that owns this subscription.",
    )
    plan = models.ForeignKey(
        "plans.Plan",
        on_delete=models.PROTECT,
        related_name="subscriptions",
        help_text="Subscription plan defining billing cadence and default policies.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    # Financial configuration snapshots
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Recurring base plan fee per billing cycle.",
    )
    tax_rate = models.ForeignKey(
        "billing.TaxRate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Applicable tax rate for billing cycles.",
    )
    discount_rule = models.ForeignKey(
        "billing.DiscountRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Applicable discount rule for billing cycles.",
    )

    # Lifecycle & schedule dates
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when service begins.",
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional contractual expiry date.",
    )
    current_period_start = models.DateField(
        null=True,
        blank=True,
        help_text="Start of the current active billing period (inclusive).",
    )
    current_period_end = models.DateField(
        null=True,
        blank=True,
        help_text="End of the current active billing period (exclusive).",
    )
    next_billing_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Next date when recurring billing worker processes this subscription.",
    )

    # Quotation validity
    quotation_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when quotation was officially issued.",
    )
    quotation_valid_until = models.DateField(
        null=True,
        blank=True,
        help_text="Last date this quotation is valid for confirmation.",
    )

    # Terms & Policies
    payment_terms_days = models.PositiveIntegerField(
        default=15,
        help_text="Payment grace period in days from invoice issue date.",
    )
    can_pause = models.BooleanField(
        default=True,
        help_text="Whether this subscription permits pausing service.",
    )
    is_paused = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if service is currently paused.",
    )
    pause_date = models.DateField(null=True, blank=True)
    pause_reason = models.CharField(max_length=255, blank=True)

    can_early_close = models.BooleanField(
        default=True,
        help_text="Whether customer or staff can close before contractual expiry.",
    )
    auto_close_on_expiry = models.BooleanField(
        default=True,
        help_text="Whether subscription automatically transitions to CLOSED on expiry.",
    )
    can_renew = models.BooleanField(
        default=True,
        help_text="Whether subscription can be extended or renewed.",
    )

    close_date = models.DateField(null=True, blank=True)
    close_reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["status", "next_billing_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    status__in=[
                        "DRAFT",
                        "QUOTATION",
                        "CONFIRMED",
                        "ACTIVE",
                        "CLOSED",
                    ]
                ),
                name="subscription_status_valid",
            ),
            models.CheckConstraint(
                check=models.Q(payment_terms_days__gte=0),
                name="subscription_payment_terms_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(base_price__gte=Decimal("0.00")),
                name="subscription_base_price_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(start_date__isnull=True, expiry_date__isnull=True)
                | models.Q(start_date__isnull=True, expiry_date__isnull=False)
                | models.Q(start_date__isnull=False, expiry_date__isnull=True)
                | models.Q(expiry_date__gte=models.F("start_date")),
                name="subscription_expiry_after_start",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number} ({self.customer.email} - {self.get_status_display()})"

    def clean(self):
        super().clean()
        if self.base_price is not None and self.base_price < Decimal("0.00"):
            raise ValidationError({"base_price": "Base plan price cannot be negative."})
        if self.payment_terms_days is not None and self.payment_terms_days < 0:
            raise ValidationError({"payment_terms_days": "Payment terms cannot be negative."})
        if self.start_date and self.expiry_date and self.expiry_date < self.start_date:
            raise ValidationError({"expiry_date": "Expiry date cannot precede start date."})
        if (
            self.current_period_start
            and self.current_period_end
            and self.current_period_end <= self.current_period_start
        ):
            raise ValidationError(
                {"current_period_end": ("Current period end date must follow period start date.")}
            )
        if (
            self.quotation_date
            and self.quotation_valid_until
            and self.quotation_valid_until < self.quotation_date
        ):
            raise ValidationError(
                {
                    "quotation_valid_until": (
                        "Quotation validity date cannot precede quotation date."
                    )
                }
            )

    @property
    def total_quantity(self) -> int:
        return sum(line.quantity for line in self.lines.all())

    @property
    def is_quotation_expired(self) -> bool:
        if self.status == self.Status.QUOTATION and self.quotation_valid_until:
            return self.quotation_valid_until < timezone.localdate()
        return False


class SubscriptionLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="+",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Number of seats or units (minimum 1).",
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Agreed unit price per cycle at subscription creation.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=1),
                name="subscription_line_quantity_min_1",
            ),
            models.CheckConstraint(
                check=models.Q(unit_price__gte=Decimal("0.00")),
                name="subscription_line_price_non_negative",
            ),
        ]

    def __str__(self) -> str:
        name = f"{self.product.name} ({self.variant.name})" if self.variant else self.product.name
        return f"{self.quantity}x {name} @ {self.unit_price}"

    def clean(self):
        super().clean()
        if self.quantity is not None and self.quantity < 1:
            raise ValidationError({"quantity": "Quantity must be at least 1."})
        if self.unit_price is not None and self.unit_price < Decimal("0.00"):
            raise ValidationError({"unit_price": "Unit price cannot be negative."})
        if self.variant_id and self.product_id:
            if self.variant.product_id != self.product_id:
                raise ValidationError(
                    {"variant": ("Selected variant does not belong to the selected product.")}
                )

    @property
    def line_gross(self) -> Decimal:
        return Decimal(self.quantity) * self.unit_price
