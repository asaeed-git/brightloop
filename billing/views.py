import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import User
from accounts.permissions import require_roles, scope_to_customer

from .forms import DiscountRuleForm, TaxRateForm
from .models import BillingRunRecord, DiscountRule, Invoice, TaxRate
from .services import run_recurring_billing


def _is_staff_or_admin(user) -> bool:
    return (
        user.is_authenticated and user.is_active and user.role in [User.Role.ADMIN, User.Role.STAFF]
    )


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


# ── Staff Invoice Views ───────────────────────────────────────────────────────


@login_required
def invoice_list(request):
    """Staff and Admin view of all customer invoices with status filtering."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)

    status_filter = request.GET.get("status", "").upper()
    queryset = Invoice.objects.select_related("customer", "subscription").all()
    today = timezone.localdate()

    if status_filter == "OVERDUE":
        queryset = queryset.filter(
            status=Invoice.Status.CONFIRMED,
            due_date__lt=today,
        )
    elif status_filter in Invoice.Status.values:
        queryset = queryset.filter(status=status_filter)

    search = request.GET.get("q", "").strip()
    if search:
        queryset = queryset.filter(number__icontains=search) | queryset.filter(
            customer__email__icontains=search
        )

    status_choices = list(Invoice.Status.choices) + [("OVERDUE", "Overdue")]

    return render(
        request,
        "billing/invoice_list.html",
        {
            "invoices": queryset,
            "status_filter": status_filter,
            "search_query": search,
            "status_choices": status_choices,
        },
    )


@login_required
def invoice_detail(request, pk):
    """Staff / Admin or authorized customer detail view of an invoice."""
    invoice = get_object_or_404(
        Invoice.objects.select_related("customer", "subscription__plan").prefetch_related(
            "lines__product", "lines__variant", "lines__discount_rule", "payments"
        ),
        pk=pk,
    )

    is_staff = _is_staff_or_admin(request.user)
    if not is_staff:
        # Enforce customer ownership
        if not request.user.is_authenticated or request.user != invoice.customer:
            raise PermissionDenied("You do not have permission to view this invoice.")

    return render(
        request,
        "billing/invoice_detail.html",
        {
            "invoice": invoice,
            "lines": invoice.lines.all(),
            "payments": invoice.payments.all(),
            "is_staff": is_staff,
        },
    )


@require_POST
def invoice_confirm(request, pk):
    """Staff action: confirm a draft invoice."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status != Invoice.Status.DRAFT:
        messages.error(
            request, f"Invoice {invoice.number} is already {invoice.get_status_display()}."
        )
    else:
        invoice.status = Invoice.Status.CONFIRMED
        invoice.save()
        messages.success(request, f"Invoice {invoice.number} has been confirmed.")

    return redirect("billing:invoice_detail", pk=invoice.pk)


@require_POST
def invoice_cancel(request, pk):
    """Staff action: cancel an unpaid invoice."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status == Invoice.Status.PAID:
        messages.error(
            request, "Cannot cancel a paid invoice without issuing a formal credit note/refund."
        )
    elif invoice.status == Invoice.Status.CANCELLED:
        messages.info(request, "Invoice is already cancelled.")
    else:
        invoice.status = Invoice.Status.CANCELLED
        invoice.save()
        messages.success(request, f"Invoice {invoice.number} has been cancelled.")

    return redirect("billing:invoice_detail", pk=invoice.pk)


def invoice_print(request, pk):
    """Print-ready layout for an invoice. Customer owner or Staff."""
    invoice = get_object_or_404(
        Invoice.objects.select_related("customer", "subscription__plan").prefetch_related(
            "lines__product", "lines__variant"
        ),
        pk=pk,
    )

    is_staff = _is_staff_or_admin(request.user)
    if not is_staff:
        if not request.user.is_authenticated or request.user != invoice.customer:
            raise PermissionDenied("You do not have access to print this invoice.")

    return render(
        request,
        "billing/invoice_print.html",
        {
            "invoice": invoice,
            "lines": invoice.lines.all(),
        },
    )


# ── Customer Portal Views ─────────────────────────────────────────────────────


@login_required
def customer_invoice_list(request):
    """Customer view of their own invoices with balance summary."""
    queryset = scope_to_customer(
        Invoice.objects.select_related("subscription__plan").order_by("-issue_date"),
        request.user,
        "customer",
    )

    total_invoiced = queryset.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    total_paid = queryset.aggregate(total=Sum("amount_paid"))["total"] or Decimal("0.00")
    total_outstanding = max(Decimal("0.00"), total_invoiced - total_paid)

    return render(
        request,
        "billing/customer_invoice_list.html",
        {
            "invoices": queryset,
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
        },
    )


@login_required
def customer_invoice_detail(request, pk):
    """Customer view of their specific invoice."""
    invoice = get_object_or_404(
        scope_to_customer(
            Invoice.objects.select_related("subscription__plan").prefetch_related(
                "lines__product", "lines__variant", "payments"
            ),
            request.user,
            "customer",
        ),
        pk=pk,
    )
    return render(
        request,
        "billing/customer_invoice_detail.html",
        {
            "invoice": invoice,
            "lines": invoice.lines.all(),
            "payments": invoice.payments.all(),
        },
    )


# ── Recurring Billing Engine Staff Views ──────────────────────────────────────


@login_required
def billing_run_list(request):
    """Staff and Admin view of historical recurring billing runs."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    runs = BillingRunRecord.objects.select_related("executed_by").all()
    today = timezone.localdate()
    return render(
        request,
        "billing/billing_run_list.html",
        {"runs": runs, "today": today},
    )


@require_POST
def billing_run_execute(request):
    """Staff trigger: execute the recurring billing engine."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)

    target_date_str = request.POST.get("target_date", "").strip()
    target_date = None
    if target_date_str:
        try:
            target_date = datetime.date.fromisoformat(target_date_str)
        except ValueError:
            messages.error(request, "Invalid target date format. Please use YYYY-MM-DD.")
            return redirect("billing:billing_run_list")

    record = run_recurring_billing(target_date=target_date, executed_by=request.user)
    if record.success:
        messages.success(
            request,
            f"Billing run for {record.run_date} completed successfully! Created {record.invoices_created} invoice(s) totalling ₹{record.total_billed_amount}.",
        )
    else:
        messages.warning(
            request,
            f"Billing run for {record.run_date} finished with errors. Created {record.invoices_created} invoice(s). See log below for details.",
        )

    return redirect("billing:billing_run_list")
