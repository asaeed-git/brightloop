"""URL patterns for public account flows (A2) and customer profile (A6)."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.ThrottledLoginView.as_view(), name="login"),
    path("logout/", views.BrightloopLogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("password-reset/", views.ThrottledPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/sent/",
        views.BrightloopPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.BrightloopPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/complete/",
        views.BrightloopPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
