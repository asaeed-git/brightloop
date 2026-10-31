from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    # Tax rates
    path("taxes/", views.tax_list, name="tax_list"),
    path("taxes/new/", views.tax_create, name="tax_create"),
    path("taxes/<uuid:pk>/edit/", views.tax_edit, name="tax_edit"),
    # Discount rules
    path("discounts/", views.discount_list, name="discount_list"),
    path("discounts/new/", views.discount_create, name="discount_create"),
    path("discounts/<uuid:pk>/edit/", views.discount_edit, name="discount_edit"),
]
