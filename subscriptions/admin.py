from django.contrib import admin

from subscriptions.models import Subscription, SubscriptionLine


class SubscriptionLineInline(admin.TabularInline):
    model = SubscriptionLine
    extra = 0
    fields = ("product", "variant", "quantity", "unit_price")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "customer",
        "plan",
        "status",
        "is_paused",
        "current_period_start",
        "current_period_end",
        "next_billing_date",
    )
    list_filter = ("status", "is_paused", "plan")
    search_fields = ("number", "customer__email", "plan__name")
    readonly_fields = ("number", "created_at", "updated_at")
    inlines = [SubscriptionLineInline]
