from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User
from accounts.permissions import require_roles

from .forms import DiscountRuleForm, TaxRateForm
from .models import DiscountRule, TaxRate

# ── Tax Rate Views ────────────────────────────────────────────────────────────


def tax_list(request):
    """List all tax rates. Admin and Staff only."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    rates = TaxRate.objects.all()
    return render(request, "billing/tax_list.html", {"rates": rates})


@require_http_methods(["GET", "POST"])
def tax_create(request):
    """Create a new tax rate. Admin and Staff only."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)

    if request.method == "POST":
        form = TaxRateForm(request.POST)
        if form.is_valid():
            rate = form.save()
            messages.success(request, f"Tax rate '{rate.name}' was created successfully.")
            return redirect("billing:tax_list")
    else:
        form = TaxRateForm()

    return render(request, "billing/tax_form.html", {"form": form, "title": "New Tax Rate"})


@require_http_methods(["GET", "POST"])
def tax_edit(request, pk):
    """Edit an existing tax rate. Admin and Staff only."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    rate = get_object_or_404(TaxRate, pk=pk)

    if request.method == "POST":
        form = TaxRateForm(request.POST, instance=rate)
        if form.is_valid():
            form.save()
            messages.success(request, f"Tax rate '{rate.name}' was updated successfully.")
            return redirect("billing:tax_list")
    else:
        form = TaxRateForm(instance=rate)

    return render(
        request,
        "billing/tax_form.html",
        {"form": form, "title": f"Edit {rate.name}", "rate": rate},
    )


# ── Discount Rule Views ───────────────────────────────────────────────────────


def discount_list(request):
    """List all discount rules. Admin and Staff only."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    rules = DiscountRule.objects.select_related("product").all()
    return render(request, "billing/discount_list.html", {"rules": rules})


@require_http_methods(["GET", "POST"])
def discount_create(request):
    """Create a new discount rule. Admin and Staff only."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)

    if request.method == "POST":
        form = DiscountRuleForm(request.POST)
        if form.is_valid():
            rule = form.save()
            messages.success(request, f"Discount rule '{rule.name}' was created successfully.")
            return redirect("billing:discount_list")
    else:
        form = DiscountRuleForm()

    return render(
        request, "billing/discount_form.html", {"form": form, "title": "New Discount Rule"}
    )


@require_http_methods(["GET", "POST"])
def discount_edit(request, pk):
    """Edit an existing discount rule. Admin and Staff only."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    rule = get_object_or_404(DiscountRule.objects.select_related("product"), pk=pk)

    if request.method == "POST":
        form = DiscountRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            messages.success(request, f"Discount rule '{rule.name}' was updated successfully.")
            return redirect("billing:discount_list")
    else:
        form = DiscountRuleForm(instance=rule)

    return render(
        request,
        "billing/discount_form.html",
        {"form": form, "title": f"Edit '{rule.name}'", "rule": rule},
    )
