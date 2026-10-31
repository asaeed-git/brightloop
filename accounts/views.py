"""
Public account views: signup, plus throttled wrappers around Django's
built-in auth views (login, logout, password reset).

All views that render forms use templates that extend base.html and the
shared components/form_fields.html partial (Syed's B1 shared UI).

Rate limiting uses accounts.throttle, which requires no extra packages.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import (
    BrightloopAuthenticationForm,
    BrightloopPasswordResetForm,
    BrightloopSetPasswordForm,
    ProfileForm,
    SignupForm,
)
from .throttle import check_throttle

_THROTTLE_MSG = (
    "Too many attempts from your location. Please wait a few minutes before trying again."
)


def signup(request):
    """
    Public signup: always creates a CUSTOMER account and logs the new user in.

    Authenticated and active users are redirected to home immediately.
    Role is never taken from POST data; SignupForm.save() enforces CUSTOMER.
    """
    if request.user.is_authenticated and request.user.is_active:
        return redirect("home")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your account has been created. Welcome to Brightloop.")
            return redirect("home")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


class ThrottledLoginView(LoginView):
    """
    Django's LoginView with:
    - our custom form (email field, normalized login)
    - rate limiting: 10 attempts per 5 minutes per IP
    - redirect already-authenticated users
    """

    form_class = BrightloopAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        if not check_throttle(request, "login", limit=10, window=300):
            form = self.get_form_class()()  # empty unbound form for redisplay
            return render(
                request,
                self.template_name,
                {"form": form, "throttle_error": _THROTTLE_MSG},
            )
        return super().post(request, *args, **kwargs)


class ThrottledPasswordResetView(PasswordResetView):
    """
    Django's PasswordResetView with:
    - our normalized email form
    - custom email/subject templates
    - rate limiting: 5 requests per 10 minutes per IP
    - does not reveal whether the email address has an account
    """

    form_class = BrightloopPasswordResetForm
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/emails/password_reset.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")

    def post(self, request, *args, **kwargs):
        if not check_throttle(request, "password_reset", limit=5, window=600):
            form = self.get_form_class()()
            return render(
                request,
                self.template_name,
                {"form": form, "throttle_error": _THROTTLE_MSG},
            )
        return super().post(request, *args, **kwargs)


class BrightloopPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class BrightloopPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = BrightloopSetPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class BrightloopPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class BrightloopLogoutView(LogoutView):
    """
    POST-only logout (Django 5 default) redirects to home.
    A GET to this URL is treated as an already-logged-out state.
    """

    next_page = "home"


@login_required
def profile(request):
    user = request.user
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile details have been updated.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=user)

    active_subs_count = user.subscriptions.filter(status="ACTIVE", is_paused=False).count()
    paused_subs_count = user.subscriptions.filter(status="ACTIVE", is_paused=True).count()
    pending_quotes_count = user.subscriptions.filter(status="QUOTATION").count()
    invoices_due_count = user.invoices.filter(status="CONFIRMED").count()

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "active_subs_count": active_subs_count,
            "paused_subs_count": paused_subs_count,
            "pending_quotes_count": pending_quotes_count,
            "invoices_due_count": invoices_due_count,
        },
    )
