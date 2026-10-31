from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.payment_list, name="payment_list"),
    path("invoices/<uuid:invoice_pk>/pay/", views.payment_create, name="payment_create"),
    path(
        "my-invoices/<uuid:invoice_pk>/pay/",
        views.customer_payment_create,
        name="customer_payment_create",
    ),
]
