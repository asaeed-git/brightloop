from django import forms

from .models import Plan, QuotationTemplate, QuotationTemplateLine


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = (
            "name",
            "code",
            "interval",
            "price",
            "min_quantity",
            "available_from",
            "available_until",
            "can_pause",
            "can_early_close",
            "auto_close_on_expiry",
            "can_renew",
            "is_active",
            "description",
        )
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Starter Monthly"}),
            "code": forms.TextInput(attrs={"placeholder": "e.g. starter-monthly"}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "min_quantity": forms.NumberInput(attrs={"min": "1"}),
            "available_from": forms.DateInput(attrs={"type": "date"}),
            "available_until": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Plan features and terms..."}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("available_from")
        end = cleaned.get("available_until")
        if start and end and start > end:
            self.add_error(
                "available_until", "Available until date must be on or after available from date."
            )
        return cleaned


class QuotationTemplateForm(forms.ModelForm):
    class Meta:
        model = QuotationTemplate
        fields = ("name", "plan", "validity_days", "notes", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Enterprise Onboarding Quote"}),
            "validity_days": forms.NumberInput(attrs={"min": "1"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Default quote terms..."}),
        }


class QuotationTemplateLineForm(forms.ModelForm):
    class Meta:
        model = QuotationTemplateLine
        fields = ("product", "variant", "quantity")
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": "1"}),
        }

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        variant = cleaned.get("variant")
        if product and variant and variant.product_id != product.id:
            self.add_error(
                "variant", f"Variant '{variant.name}' does not belong to product '{product.name}'."
            )
        return cleaned
