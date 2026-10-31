from django.contrib import admin

from accounts.models import User

from .models import Plan, QuotationTemplate, QuotationTemplateLine


class QuotationTemplateLineInline(admin.TabularInline):
    model = QuotationTemplateLine
    extra = 1
    fields = ("product", "variant", "quantity")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "interval",
        "price",
        "min_quantity",
        "available_from",
        "available_until",
        "is_active",
    )
    list_filter = (
        "interval",
        "is_active",
        "can_pause",
        "can_early_close",
        "auto_close_on_expiry",
        "can_renew",
    )
    search_fields = ("name", "code", "description")
    prepopulated_fields = {"code": ("name",)}

    def has_module_permission(self, request):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
            and super().has_module_permission(request)
        )


@admin.register(QuotationTemplate)
class QuotationTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "plan", "validity_days", "is_active", "created_at")
    list_filter = ("is_active", "plan__interval")
    search_fields = ("name", "notes", "plan__name")
    inlines = [QuotationTemplateLineInline]

    def has_module_permission(self, request):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
            and super().has_module_permission(request)
        )
