"""Payment settlement service for Brightloop.

All money-mutating operations run inside a single ``transaction.atomic()``
block with a row-level lock on the invoice row (``select_for_update``).
This prevents concurrent double-payments without relying on application-level
race protection.

Idempotency contract
--------------------
* Same ``idempotency_key`` **and** matching payload → return the existing
  ``Payment`` object unchanged (no new database row, no invoice mutation).
* Same ``idempotency_key`` **but** different ``amount`` or ``method``
  → raise ``PaymentConflictError``.

Overpayment protection
----------------------
``amount`` must be ≤ ``invoice.amount_due`` at the time the lock is
acquired.  Attempts exceeding this limit raise ``OverpaymentError`` and
leave the invoice state untouched.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from billing.models import Invoice

from .models import Payment


class PaymentError(Exception):
    """Base class for payment service errors."""


class OverpaymentError(PaymentError):
    """Raised when the requested amount exceeds the invoice balance due."""


class PaymentConflictError(PaymentError):
    """Raised when an idempotency key is reused with a conflicting payload."""


class InvalidPaymentError(PaymentError):
    """Raised when the invoice is not in a payable state."""


def record_payment(
    *,
    invoice: Invoice,
    amount: Decimal,
    method: str,
    idempotency_key: str,
    transaction_ref: str = "",
    notes: str = "",
    paid_at=None,
) -> Payment:
    """Record a payment against *invoice* and update its balance atomically.

    Parameters
    ----------
    invoice:
        The ``Invoice`` instance to pay.  Must be in ``CONFIRMED`` status.
    amount:
        INR amount to apply.  Must be positive and ≤ ``invoice.amount_due``.
    method:
        One of ``Payment.Method`` text choices.
    idempotency_key:
        Caller-supplied string that uniquely identifies this payment attempt.
    transaction_ref:
        Optional external reference (bank UTR, card auth code, etc.).
    notes:
        Optional internal notes.
    paid_at:
        Optional explicit payment timestamp; defaults to ``timezone.now()``.

    Returns
    -------
    Payment
        The created (or existing, in case of idempotent replay) ``Payment``
        record.

    Raises
    ------
    InvalidPaymentError
        If the invoice is not in ``CONFIRMED`` status.
    OverpaymentError
        If ``amount`` exceeds ``invoice.amount_due``.
    PaymentConflictError
        If ``idempotency_key`` is reused with a different ``amount`` or
        ``method``.
    """
    amount = Decimal(amount).quantize(Decimal("0.01"))

    with transaction.atomic():
        # --- Idempotency check (outside the lock: key is unique-indexed) ------
        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            # Same payload → idempotent replay; return existing record.
            if existing.amount == amount and existing.method == method:
                return existing
            # Different payload → conflict.
            raise PaymentConflictError(
                f"Idempotency key '{idempotency_key}' was already used with "
                f"amount=₹{existing.amount} method={existing.method}. "
                f"Submitted amount=₹{amount} method={method} does not match."
            )

        # --- Row-level lock on the invoice ------------------------------------
        locked_invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)

        # Invoice must be in a payable state
        if locked_invoice.status != Invoice.Status.CONFIRMED:
            raise InvalidPaymentError(
                f"Invoice {locked_invoice.number} is in status "
                f"'{locked_invoice.get_status_display()}' and cannot accept payments. "
                f"Only CONFIRMED invoices are payable."
            )

        amount_due = locked_invoice.amount_due
        if amount > amount_due:
            raise OverpaymentError(
                f"Payment of ₹{amount} exceeds the outstanding balance of "
                f"₹{amount_due} on invoice {locked_invoice.number}."
            )

        # --- Create Payment record -------------------------------------------
        payment = Payment.objects.create(
            invoice=locked_invoice,
            customer=locked_invoice.customer,
            idempotency_key=idempotency_key,
            method=method,
            amount=amount,
            paid_at=paid_at or timezone.now(),
            transaction_ref=transaction_ref,
            notes=notes,
        )

        # --- Update invoice balance ------------------------------------------
        locked_invoice.amount_paid = (locked_invoice.amount_paid + amount).quantize(Decimal("0.01"))

        if locked_invoice.amount_paid >= locked_invoice.total:
            # Full settlement
            locked_invoice.status = Invoice.Status.PAID
            locked_invoice.paid_at = payment.paid_at

        locked_invoice.save(update_fields=["amount_paid", "status", "paid_at", "updated_at"])

    return payment
