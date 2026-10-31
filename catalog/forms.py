from decimal import Decimal

from django import forms

from .models import Product, ProductVariant


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("name", "product_type", "sales_price", "cost_price", "notes", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Cloud Storage"}),
            "sales_price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "cost_price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Internal product notes..."}),
        }


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ("name", "attribute_name", "attribute_value", "price_extra", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Enterprise Tier"}),
            "attribute_name": forms.TextInput(attrs={"placeholder": "e.g. Edition"}),
            "attribute_value": forms.TextInput(attrs={"placeholder": "e.g. Enterprise"}),
            "price_extra": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product or (
            self.instance.product if self.instance and self.instance.pk else None
        )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if self.product:
            qs = ProductVariant.objects.filter(product=self.product, name__iexact=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"A variant named '{name}' already exists for this product."
                )
        return name

    def clean(self):
        cleaned = super().clean()
        price_extra = cleaned.get("price_extra")
        if self.product and price_extra is not None:
            if self.product.sales_price + price_extra < Decimal("0.00"):
                self.add_error(
                    "price_extra",
                    "Effective sales price (base product price + variant adjustment) cannot be negative.",
                )
        return cleaned
