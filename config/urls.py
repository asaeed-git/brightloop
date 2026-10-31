from django.contrib import admin
from django.urls import path

from core.views import health, home

admin.site.site_header = "Brightloop administration"
admin.site.site_title = "Brightloop"
urlpatterns = [
    path("", home, name="home"),
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
]
