from django.contrib import admin

from .models import DiscountRule, TaxRate


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ("name", "rate", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(DiscountRule)
class DiscountRuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "kind",
        "value",
        "scope",
        "product",
        "is_active",
        "valid_from",
        "valid_until",
    )
    list_filter = ("kind", "scope", "is_active")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("product",)
