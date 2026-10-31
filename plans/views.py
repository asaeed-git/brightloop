from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import User
from accounts.permissions import require_roles
from pricing.services import Charge, calculate_price

from .forms import PlanForm, QuotationTemplateForm, QuotationTemplateLineForm
from .models import Plan, QuotationTemplate, QuotationTemplateLine


def _is_staff_or_admin(user) -> bool:
    return (
        user.is_authenticated and user.is_active and user.role in [User.Role.ADMIN, User.Role.STAFF]
    )


def plan_list(request):
    """
    List billing plans.
    Staff/Admin: see all plans (including inactive and unavailable).
    Public/Customer: see only active, available plans.
    """
    is_staff = _is_staff_or_admin(request.user)
    today = timezone.localdate()

    if is_staff:
        plans = Plan.objects.all()
    else:
        plans = [p for p in Plan.objects.filter(is_active=True) if p.is_available_on(today)]

    return render(
        request,
        "plans/plan_list.html",
        {"plans": plans, "is_staff": is_staff, "today": today},
    )


def plan_detail(request, pk):
    is_staff = _is_staff_or_admin(request.user)
    if is_staff:
        plan = get_object_or_404(Plan, pk=pk)
    else:
        plan = get_object_or_404(Plan, pk=pk, is_active=True)
        if not plan.is_available_on():
            messages.warning(request, "This plan is currently not available for new subscriptions.")

    return render(
        request,
        "plans/plan_detail.html",
        {"plan": plan, "is_staff": is_staff},
    )


@require_http_methods(["GET", "POST"])
def plan_create(request):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)

    if request.method == "POST":
        form = PlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f"Plan '{plan.name}' was created successfully.")
            return redirect("plans:plan_detail", pk=plan.pk)
    else:
        form = PlanForm()

    return render(
        request, "plans/plan_form.html", {"form": form, "title": "Create Subscription Plan"}
    )


@require_http_methods(["GET", "POST"])
def plan_edit(request, pk):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    plan = get_object_or_404(Plan, pk=pk)

    if request.method == "POST":
        form = PlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, f"Plan '{plan.name}' was updated successfully.")
            return redirect("plans:plan_detail", pk=plan.pk)
    else:
        form = PlanForm(instance=plan)

    return render(
        request,
        "plans/plan_form.html",
        {"form": form, "title": f"Edit {plan.name}", "plan": plan},
    )


# ── Quotation Templates (Staff / Admin) ───────────────────────────────────


@login_required
def template_list(request):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    templates = QuotationTemplate.objects.select_related("plan").prefetch_related("lines").all()
    return render(
        request,
        "plans/template_list.html",
        {"templates": templates},
    )


@login_required
def template_detail(request, pk):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    template = get_object_or_404(
        QuotationTemplate.objects.select_related("plan").prefetch_related(
            "lines__product", "lines__variant"
        ),
        pk=pk,
    )
    lines = template.lines.all()

    # Calculate pricing preview using pure B2 calculation service
    charges = []
    # 1. Base Plan Charge
    if template.plan.price > Decimal("0.00"):
        charges.append(
            Charge(
                charge_id=f"plan_{template.plan.id}",
                quantity=1,
                unit_price=template.plan.price,
                variant_adjustment=Decimal("0.00"),
            )
        )
    # 2. Product Line Charges
    for line in lines:
        extra = line.variant.price_extra if line.variant else Decimal("0.00")
        charges.append(
            Charge(
                charge_id=f"line_{line.id}",
                quantity=line.quantity,
                unit_price=line.product.sales_price,
                variant_adjustment=extra,
                product_id=str(line.product.id),
            )
        )

    preview_total = calculate_price(charges) if charges else None

    return render(
        request,
        "plans/template_detail.html",
        {
            "template": template,
            "lines": lines,
            "preview_total": preview_total,
            "line_form": QuotationTemplateLineForm(),
        },
    )


@require_http_methods(["GET", "POST"])
def template_create(request):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)

    if request.method == "POST":
        form = QuotationTemplateForm(request.POST)
        if form.is_valid():
            template = form.save()
            messages.success(request, f"Quotation template '{template.name}' created.")
            return redirect("plans:template_detail", pk=template.pk)
    else:
        form = QuotationTemplateForm()

    return render(
        request, "plans/template_form.html", {"form": form, "title": "New Quotation Template"}
    )


@require_http_methods(["GET", "POST"])
def template_edit(request, pk):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    template = get_object_or_404(QuotationTemplate, pk=pk)

    if request.method == "POST":
        form = QuotationTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, f"Template '{template.name}' updated.")
            return redirect("plans:template_detail", pk=template.pk)
    else:
        form = QuotationTemplateForm(instance=template)

    return render(
        request,
        "plans/template_form.html",
        {"form": form, "title": f"Edit {template.name}", "template": template},
    )


@require_POST
def template_line_create(request, pk):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    template = get_object_or_404(QuotationTemplate, pk=pk)
    form = QuotationTemplateLineForm(request.POST)
    if form.is_valid():
        line = form.save(commit=False)
        line.template = template
        line.save()
        messages.success(request, f"Added {line.product.name} to template.")
    else:
        for error in form.errors.values():
            messages.error(request, error)
    return redirect("plans:template_detail", pk=template.pk)


@require_POST
def template_line_delete(request, pk, line_pk):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    template = get_object_or_404(QuotationTemplate, pk=pk)
    line = get_object_or_404(QuotationTemplateLine, pk=line_pk, template=template)
    line.delete()
    messages.success(request, "Template line removed.")
    return redirect("plans:template_detail", pk=template.pk)
