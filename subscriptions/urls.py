from django.urls import path

from subscriptions import views

app_name = "subscriptions"

urlpatterns = [
    path("", views.subscription_list, name="subscription_list"),
    path("new/", views.subscription_create, name="subscription_create"),
    path("from-template/", views.subscription_from_template, name="subscription_from_template"),
    path("<uuid:pk>/", views.subscription_detail, name="subscription_detail"),
    path("<uuid:pk>/edit/", views.subscription_edit, name="subscription_edit"),
    path("<uuid:pk>/lines/new/", views.subscription_line_add, name="subscription_line_add"),
    path(
        "<uuid:pk>/lines/<uuid:line_pk>/delete/",
        views.subscription_line_delete,
        name="subscription_line_delete",
    ),
    path(
        "<uuid:pk>/lines/<uuid:line_pk>/update-quantity/",
        views.subscription_line_update_quantity,
        name="subscription_line_update_quantity",
    ),
    path(
        "<uuid:pk>/transition/<str:action>/",
        views.subscription_transition,
        name="subscription_transition",
    ),
]
