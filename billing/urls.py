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
    # Staff invoice management
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/<uuid:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<uuid:pk>/confirm/", views.invoice_confirm, name="invoice_confirm"),
    path("invoices/<uuid:pk>/cancel/", views.invoice_cancel, name="invoice_cancel"),
    path("invoices/<uuid:pk>/print/", views.invoice_print, name="invoice_print"),
    # Customer Portal
    path("my-invoices/", views.customer_invoice_list, name="customer_invoice_list"),
    path("my-invoices/<uuid:pk>/", views.customer_invoice_detail, name="customer_invoice_detail"),
    # Recurring billing worker / audit runs
    path("runs/", views.billing_run_list, name="billing_run_list"),
    path("runs/execute/", views.billing_run_execute, name="billing_run_execute"),
]
