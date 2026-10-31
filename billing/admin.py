from django.contrib import admin

from .models import BillingRunRecord, DiscountRule, Invoice, InvoiceLine, TaxRate


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


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = (
        "id",
        "description",
        "quantity",
        "unit_price",
        "gross",
        "discount",
        "net",
        "tax",
        "total",
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "customer",
        "status",
        "issue_date",
        "due_date",
        "total",
        "amount_paid",
    )
    list_filter = ("status", "issue_date")
    search_fields = ("number", "customer__email")
    readonly_fields = (
        "id",
        "number",
        "subtotal",
        "discount_total",
        "net_total",
        "tax_total",
        "total",
        "created_at",
        "updated_at",
    )
    inlines = [InvoiceLineInline]


@admin.register(BillingRunRecord)
class BillingRunRecordAdmin(admin.ModelAdmin):
    list_display = (
        "run_date",
        "executed_at",
        "executed_by",
        "invoices_created",
        "total_billed_amount",
        "success",
    )
    list_filter = ("success", "run_date")
    readonly_fields = ("id", "executed_at", "log_summary")
