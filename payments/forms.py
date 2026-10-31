from decimal import Decimal

from django import forms

from .models import Payment


class PaymentForm(forms.Form):
    """Form for recording a payment against an invoice."""

    method = forms.ChoiceField(
        choices=Payment.Method.choices,
        label="Payment Method",
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        label="Amount (₹)",
    )
    transaction_ref = forms.CharField(
        max_length=255,
        required=False,
        label="Transaction Reference",
        help_text="Bank UTR, card auth code, or other external reference.",
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Notes",
    )
    idempotency_key = forms.UUIDField(
        required=False,
        label="Idempotency Key",
        help_text="Leave blank to auto-generate. Supply a UUID to make this request idempotent.",
    )
