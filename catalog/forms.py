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
