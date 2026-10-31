from django.contrib import admin
from django.urls import include, path

from core.views import health, home

admin.site.site_header = "Brightloop administration"
admin.site.site_title = "Brightloop"
urlpatterns = [
    path("", home, name="home"),
    path("health/", health, name="health"),
    path("accounts/", include("accounts.urls")),
    path("catalog/", include("catalog.urls")),
    path("plans/", include("plans.urls")),
    path("admin/", admin.site.urls),
]
