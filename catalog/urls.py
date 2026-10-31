from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<uuid:pk>/", views.product_detail, name="product_detail"),
    path("products/<uuid:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<uuid:product_pk>/variants/new/", views.variant_create, name="variant_create"),
    path("variants/<uuid:pk>/edit/", views.variant_edit, name="variant_edit"),
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/<uuid:pk>/", views.customer_detail, name="customer_detail"),
]
