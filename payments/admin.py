from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice",
        "customer",
        "method",
        "amount",
        "paid_at",
        "transaction_ref",
    )
    list_filter = ("method", "paid_at")
    search_fields = (
        "invoice__number",
        "customer__email",
        "transaction_ref",
        "idempotency_key",
    )
    readonly_fields = ("id", "created_at", "idempotency_key")
