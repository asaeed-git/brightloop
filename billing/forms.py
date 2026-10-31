from django import forms
from django.core.exceptions import ValidationError

from .models import DiscountRule, TaxRate


class TaxRateForm(forms.ModelForm):
    class Meta:
        model = TaxRate
        fields = ("name", "rate", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. GST 18%"}),
            "rate": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
        }

    def clean_rate(self):
        rate = self.cleaned_data.get("rate")
        if rate is not None and (rate < 0 or rate > 100):
            raise ValidationError("Tax rate must be between 0.00 and 100.00.")
        return rate


class DiscountRuleForm(forms.ModelForm):
    class Meta:
        model = DiscountRule
        fields = (
            "name",
            "kind",
            "value",
            "scope",
            "product",
            "min_eligible_gross",
            "valid_from",
            "valid_until",
            "max_uses",
            "is_active",
        )
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. New Customer 10% Off"}),
            "value": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "min_eligible_gross": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "placeholder": "Leave blank for no minimum"}
            ),
            "valid_from": forms.DateInput(attrs={"type": "date"}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
            "max_uses": forms.NumberInput(
                attrs={"min": "1", "placeholder": "Leave blank for unlimited"}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        value = cleaned.get("value")
        scope = cleaned.get("scope")
        product = cleaned.get("product")
        valid_from = cleaned.get("valid_from")
        valid_until = cleaned.get("valid_until")

        # Percentage cap
        if kind == DiscountRule.Kind.PERCENTAGE and value is not None:
            if value <= 0 or value > 100:
                self.add_error("value", "Percentage discount must be between 0.01 and 100.00.")

        # Fixed discount: require cent precision
        if kind == DiscountRule.Kind.FIXED and value is not None:
            cents = value * 100
            if cents != cents.to_integral_value():
                self.add_error(
                    "value", "Fixed discount amount must have at most two decimal places."
                )
            if value <= 0:
                self.add_error("value", "Fixed discount amount must be positive.")

        # Scope / product consistency
        if scope == DiscountRule.Scope.PRODUCT and not product:
            self.add_error(
                "product", "A product must be selected when scope is 'Specific product lines only'."
            )
        if scope == DiscountRule.Scope.SUBSCRIPTION and product:
            self.add_error(
                "product",
                "Leave product blank when scope is 'Whole subscription'. "
                "A product-scoped rule requires scope 'Specific product lines only'.",
            )

        # Date range coherence
        if valid_from and valid_until and valid_until < valid_from:
            self.add_error("valid_until", "'Valid until' must be on or after 'Valid from'.")

        return cleaned
