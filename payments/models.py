import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Payment(models.Model):
    """Records a single settled payment against an invoice.

    Each payment carries an idempotency_key so that retried or replayed
    requests are safe: the same key with the same payload returns the
    existing payment; the same key with a different payload is rejected
    as a conflict.  All amounts are in INR with two decimal places.
    """

    class Method(models.TextChoices):
        CARD = "CARD", "Credit / Debit Card"
        UPI = "UPI", "UPI"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        CASH = "CASH", "Cash"
        SIMULATED = "SIMULATED", "Simulated (Demo)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        "billing.Invoice",
        on_delete=models.PROTECT,
        related_name="payments",
        help_text="Invoice this payment settles (in full or partially).",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
        help_text="Customer who made the payment.",
    )
    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
        help_text=(
            "Caller-supplied key that guarantees at-most-once processing. "
            "Replaying the same key and payload returns the original record."
        ),
    )
    method = models.CharField(
        max_length=20,
        choices=Method.choices,
        help_text="Payment channel used.",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Payment amount in INR (must be positive; must not exceed invoice.amount_due).",
    )
    paid_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when the payment was received.",
    )
    transaction_ref = models.CharField(
        max_length=255,
        blank=True,
        help_text="External transaction reference (bank UTR, card auth code, etc.).",
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes recorded alongside the payment.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at", "-created_at"]
        indexes = [
            models.Index(fields=["invoice"]),
            models.Index(fields=["customer", "-paid_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="payments_payment_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_method_display()} ₹{self.amount} "
            f"for {self.invoice.number} ({self.customer.email})"
        )
