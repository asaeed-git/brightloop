from django.contrib import admin

from accounts.models import User

from .models import Product, ProductVariant


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("name", "attribute_name", "attribute_value", "price_extra", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "product_type", "sales_price", "cost_price", "is_active", "created_at")
    list_filter = ("product_type", "is_active")
    search_fields = ("name", "notes")
    inlines = [ProductVariantInline]

    def has_module_permission(self, request):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
            and super().has_module_permission(request)
        )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("name", "product", "price_extra", "effective_sales_price", "is_active")
    list_filter = ("is_active", "product")
    search_fields = ("name", "product__name", "attribute_name", "attribute_value")

    def has_module_permission(self, request):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
            and super().has_module_permission(request)
        )
