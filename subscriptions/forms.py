from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from billing.models import DiscountRule, TaxRate
from catalog.models import Product, ProductVariant
from plans.models import Plan, QuotationTemplate
from subscriptions.models import Subscription, SubscriptionLine

User = get_user_model()


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = [
            "customer",
            "plan",
            "base_price",
            "tax_rate",
            "discount_rule",
            "start_date",
            "expiry_date",
            "payment_terms_days",
            "quotation_valid_until",
            "can_pause",
            "can_early_close",
            "can_renew",
            "auto_close_on_expiry",
            "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "quotation_valid_until": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = User.objects.filter(
            role=User.Role.CUSTOMER, is_active=True
        ).order_by("email")
        self.fields["plan"].queryset = Plan.objects.filter(is_active=True).order_by("name")
        self.fields["tax_rate"].queryset = TaxRate.objects.filter(is_active=True).order_by("name")
        self.fields["discount_rule"].queryset = DiscountRule.objects.filter(
            is_active=True
        ).order_by("name")

        if not self.instance.pk:
            self.fields["start_date"].initial = timezone.localdate()

    def clean(self):
        cleaned_data = super().clean()
        plan = cleaned_data.get("plan")
        base_price = cleaned_data.get("base_price")

        # If base_price was not explicitly specified, default to plan.price
        if (base_price is None or base_price == Decimal("0.00")) and plan:
            cleaned_data["base_price"] = plan.price

        start_date = cleaned_data.get("start_date")
        expiry_date = cleaned_data.get("expiry_date")
        if start_date and expiry_date and expiry_date < start_date:
            self.add_error("expiry_date", "Expiry date cannot precede start date.")

        return cleaned_data


class SubscriptionFromTemplateForm(forms.Form):
    customer = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Customer Account",
        help_text="Customer user who will receive this quotation.",
    )
    template = forms.ModelChoiceField(
        queryset=QuotationTemplate.objects.none(),
        label="Quotation Template",
        help_text="Pre-configured template with plan and default line items.",
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Contract Start Date",
        initial=timezone.localdate,
        help_text="Default is today.",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Quotation Notes",
        help_text="Optional custom terms or notes for the quotation.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = User.objects.filter(
            role=User.Role.CUSTOMER, is_active=True
        ).order_by("email")
        self.fields["template"].queryset = QuotationTemplate.objects.select_related(
            "plan"
        ).order_by("name")


class SubscriptionLineForm(forms.ModelForm):
    class Meta:
        model = SubscriptionLine
        fields = ["product", "variant", "quantity", "unit_price"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True).order_by("name")
        self.fields["variant"].queryset = ProductVariant.objects.select_related("product").order_by(
            "product__name", "name"
        )
        self.fields["unit_price"].required = False

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        variant = cleaned_data.get("variant")
        quantity = cleaned_data.get("quantity")
        unit_price = cleaned_data.get("unit_price")

        if quantity is not None and quantity < 1:
            self.add_error("quantity", "Quantity must be at least 1.")

        if variant and product and variant.product_id != product.id:
            self.add_error("variant", "Selected variant does not belong to the selected product.")

        if product and (unit_price is None or unit_price < Decimal("0.00")):
            if variant:
                cleaned_data["unit_price"] = variant.effective_sales_price
            else:
                cleaned_data["unit_price"] = product.sales_price

        return cleaned_data
