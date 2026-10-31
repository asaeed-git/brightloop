from django.urls import path

from . import views

app_name = "plans"

urlpatterns = [
    path("", views.plan_list, name="plan_list"),
    path("new/", views.plan_create, name="plan_create"),
    path("<uuid:pk>/", views.plan_detail, name="plan_detail"),
    path("<uuid:pk>/edit/", views.plan_edit, name="plan_edit"),
    path("templates/", views.template_list, name="template_list"),
    path("templates/new/", views.template_create, name="template_create"),
    path("templates/<uuid:pk>/", views.template_detail, name="template_detail"),
    path("templates/<uuid:pk>/edit/", views.template_edit, name="template_edit"),
    path("templates/<uuid:pk>/lines/new/", views.template_line_create, name="template_line_create"),
    path(
        "templates/<uuid:pk>/lines/<uuid:line_pk>/delete/",
        views.template_line_delete,
        name="template_line_delete",
    ),
]
