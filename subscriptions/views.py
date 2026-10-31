import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import require_roles
from subscriptions.forms import (
    SubscriptionForm,
    SubscriptionFromTemplateForm,
    SubscriptionLineForm,
)
from subscriptions.models import Subscription, SubscriptionLine
from subscriptions.services import (
    calculate_subscription_pricing,
    close_subscription,
    create_subscription_from_template,
    pause_subscription,
    renew_subscription,
    resume_subscription,
    transition_to_active,
    transition_to_confirmed,
    transition_to_quotation,
)

User = get_user_model()


@login_required
def subscription_list(request):
    is_internal = request.user.role in [User.Role.ADMIN, User.Role.STAFF]
    queryset = Subscription.objects.select_related("customer", "plan", "tax_rate", "discount_rule")

    if not is_internal:
        queryset = queryset.filter(customer=request.user)

    status_filter = request.GET.get("status")
    if status_filter in [c[0] for c in Subscription.Status.choices]:
        queryset = queryset.filter(status=status_filter)
    elif status_filter == "PAUSED":
        queryset = queryset.filter(status=Subscription.Status.ACTIVE, is_paused=True)

    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(
            Q(number__icontains=query)
            | Q(customer__email__icontains=query)
            | Q(plan__name__icontains=query)
        )

    # Status counts for navigation badges
    base_qs = (
        Subscription.objects.all()
        if is_internal
        else Subscription.objects.filter(customer=request.user)
    )
    counts = {
        "ALL": base_qs.count(),
        "DRAFT": base_qs.filter(status=Subscription.Status.DRAFT).count(),
        "QUOTATION": base_qs.filter(status=Subscription.Status.QUOTATION).count(),
        "CONFIRMED": base_qs.filter(status=Subscription.Status.CONFIRMED).count(),
        "ACTIVE": base_qs.filter(status=Subscription.Status.ACTIVE, is_paused=False).count(),
        "PAUSED": base_qs.filter(status=Subscription.Status.ACTIVE, is_paused=True).count(),
        "CLOSED": base_qs.filter(status=Subscription.Status.CLOSED).count(),
    }

    return render(
        request,
        "subscriptions/subscription_list.html",
        {
            "subscriptions": queryset,
            "counts": counts,
            "current_status": status_filter or "ALL",
            "query": query,
            "is_internal": is_internal,
        },
    )


@login_required
def subscription_detail(request, pk):
    is_internal = request.user.role in [User.Role.ADMIN, User.Role.STAFF]
    queryset = (
        Subscription.objects.select_related("customer", "plan", "tax_rate", "discount_rule")
        .prefetch_related("lines__product", "lines__variant", "invoices")
        .all()
    )

    if not is_internal:
        queryset = queryset.filter(customer=request.user)

    subscription = get_object_or_404(queryset, pk=pk)
    lines = subscription.lines.all()
    invoices = subscription.invoices.all()

    # Calculate live pricing breakdown via pure calculator
    pricing = calculate_subscription_pricing(subscription)

    line_form = None
    if is_internal and subscription.status in [
        Subscription.Status.DRAFT,
        Subscription.Status.QUOTATION,
    ]:
        line_form = SubscriptionLineForm()

    return render(
        request,
        "subscriptions/subscription_detail.html",
        {
            "subscription": subscription,
            "lines": lines,
            "invoices": invoices,
            "pricing": pricing,
            "line_form": line_form,
            "is_internal": is_internal,
        },
    )


@login_required
def subscription_create(request):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.status = Subscription.Status.DRAFT
            subscription.save()
            messages.success(
                request,
                f"Draft subscription {subscription.number} created. Now add line items.",
            )
            return redirect("subscriptions:subscription_detail", pk=subscription.pk)
    else:
        form = SubscriptionForm()

    return render(
        request,
        "subscriptions/subscription_form.html",
        {"form": form, "title": "Create Subscription Draft"},
    )


@login_required
def subscription_from_template(request):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    if request.method == "POST":
        form = SubscriptionFromTemplateForm(request.POST)
        if form.is_valid():
            customer = form.cleaned_data["customer"]
            template = form.cleaned_data["template"]
            start_date = form.cleaned_data.get("start_date")
            notes = form.cleaned_data.get("notes")

            subscription = create_subscription_from_template(
                template=template,
                customer=customer,
                start_date=start_date,
                notes=notes,
            )
            messages.success(
                request,
                f"Quotation {subscription.number} generated from template '{template.name}'.",
            )
            return redirect("subscriptions:subscription_detail", pk=subscription.pk)
    else:
        initial = {}
        template_pk = request.GET.get("template")
        if template_pk:
            initial["template"] = template_pk
        form = SubscriptionFromTemplateForm(initial=initial)

    return render(
        request,
        "subscriptions/subscription_from_template.html",
        {"form": form},
    )


@login_required
def subscription_edit(request, pk):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    subscription = get_object_or_404(Subscription, pk=pk)

    if subscription.status not in [
        Subscription.Status.DRAFT,
        Subscription.Status.QUOTATION,
    ]:
        messages.error(
            request,
            f"Cannot edit terms for subscription in '{subscription.get_status_display()}' status.",
        )
        return redirect("subscriptions:subscription_detail", pk=subscription.pk)

    if request.method == "POST":
        form = SubscriptionForm(request.POST, instance=subscription)
        if form.is_valid():
            form.save()
            messages.success(request, f"Subscription {subscription.number} updated.")
            return redirect("subscriptions:subscription_detail", pk=subscription.pk)
    else:
        form = SubscriptionForm(instance=subscription)

    return render(
        request,
        "subscriptions/subscription_form.html",
        {
            "form": form,
            "title": f"Edit Subscription {subscription.number}",
            "subscription": subscription,
        },
    )


@login_required
@require_POST
def subscription_line_add(request, pk):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    subscription = get_object_or_404(Subscription, pk=pk)

    if subscription.status not in [
        Subscription.Status.DRAFT,
        Subscription.Status.QUOTATION,
    ]:
        messages.error(request, "Lines can only be modified on Draft or Quotation subscriptions.")
        return redirect("subscriptions:subscription_detail", pk=subscription.pk)

    form = SubscriptionLineForm(request.POST)
    if form.is_valid():
        line = form.save(commit=False)
        line.subscription = subscription
        line.save()
        messages.success(request, f"Added line {line}.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field.capitalize()}: {error}")

    return redirect("subscriptions:subscription_detail", pk=subscription.pk)


@login_required
@require_POST
def subscription_line_delete(request, pk, line_pk):
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    subscription = get_object_or_404(Subscription, pk=pk)
    line = get_object_or_404(SubscriptionLine, pk=line_pk, subscription=subscription)

    if subscription.status not in [
        Subscription.Status.DRAFT,
        Subscription.Status.QUOTATION,
    ]:
        messages.error(request, "Lines can only be deleted on Draft or Quotation subscriptions.")
        return redirect("subscriptions:subscription_detail", pk=subscription.pk)

    line.delete()
    messages.success(request, "Line item removed.")
    return redirect("subscriptions:subscription_detail", pk=subscription.pk)


@login_required
@require_POST
def subscription_line_update_quantity(request, pk, line_pk):
    is_internal = request.user.role in [User.Role.ADMIN, User.Role.STAFF]
    queryset = (
        Subscription.objects.all()
        if is_internal
        else Subscription.objects.filter(customer=request.user)
    )
    subscription = get_object_or_404(queryset, pk=pk)
    line = get_object_or_404(SubscriptionLine, pk=line_pk, subscription=subscription)

    if subscription.status not in [
        Subscription.Status.ACTIVE,
        Subscription.Status.DRAFT,
        Subscription.Status.QUOTATION,
    ]:
        messages.error(request, "Line quantity cannot be modified on a closed subscription.")
        return redirect("subscriptions:subscription_detail", pk=subscription.pk)

    try:
        new_quantity = int(request.POST.get("quantity", 0))
        if new_quantity < 1:
            raise ValidationError("Quantity must be at least 1.")

        other_qty = sum(sub_line.quantity for sub_line in subscription.lines.exclude(pk=line.pk))
        if other_qty + new_quantity < subscription.plan.min_quantity:
            raise ValidationError(
                f"Total quantity ({other_qty + new_quantity}) would be below the"
                f" plan's minimum required seats ({subscription.plan.min_quantity})."
            )

        line.quantity = new_quantity
        line.save()
        messages.success(request, f"Updated {line.product.name} quantity to {new_quantity}.")
    except ValidationError as exc:
        messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
    except ValueError:
        messages.error(request, "Please enter a valid whole number for quantity.")

    return redirect("subscriptions:subscription_detail", pk=subscription.pk)


@login_required
@require_POST
def subscription_transition(request, pk, action):
    is_internal = request.user.role in [User.Role.ADMIN, User.Role.STAFF]
    queryset = (
        Subscription.objects.all()
        if is_internal
        else Subscription.objects.filter(customer=request.user)
    )
    subscription = get_object_or_404(queryset, pk=pk)

    try:
        if action == "send_quote":
            require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
            validity_days_raw = request.POST.get("validity_days")
            validity_days = int(validity_days_raw) if validity_days_raw else None
            transition_to_quotation(subscription, validity_days=validity_days)
            messages.success(
                request,
                f"Quotation issued for {subscription.number}. Valid until {subscription.quotation_valid_until}.",
            )

        elif action == "confirm":
            # Both staff and customer can confirm their own quotation
            transition_to_confirmed(subscription, confirmed_by=request.user)
            messages.success(
                request,
                f"Subscription {subscription.number} confirmed.",
            )

        elif action == "activate":
            require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
            start_date_raw = request.POST.get("start_date")
            start_date = datetime.date.fromisoformat(start_date_raw) if start_date_raw else None
            transition_to_active(subscription, start_date=start_date)
            messages.success(
                request,
                f"Subscription {subscription.number} is now ACTIVE. Current period: {subscription.current_period_start} to {subscription.current_period_end}.",
            )

        elif action == "pause":
            reason = request.POST.get("reason", "")
            pause_subscription(subscription, reason=reason)
            messages.success(request, f"Subscription {subscription.number} paused.")

        elif action == "resume":
            resume_subscription(subscription)
            messages.success(request, f"Subscription {subscription.number} resumed.")

        elif action == "close":
            reason = request.POST.get("reason", "").strip()
            if not is_internal:
                # Customer self-serve cancellation
                if (
                    subscription.status == Subscription.Status.ACTIVE
                    and not subscription.can_early_close
                ):
                    raise ValidationError(
                        "This subscription does not permit early cancellation before"
                        f" contract expiry ({subscription.expiry_date})."
                    )
                if not reason:
                    reason = "Cancelled by customer"
            close_subscription(subscription, reason=reason)
            messages.success(request, f"Subscription {subscription.number} has been closed.")

        elif action == "renew":
            require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
            new_expiry_raw = request.POST.get("new_expiry_date")
            if not new_expiry_raw:
                raise ValidationError("Please provide a new expiry date.")
            new_expiry_date = datetime.date.fromisoformat(new_expiry_raw)
            renew_subscription(subscription, new_expiry_date=new_expiry_date)
            messages.success(
                request,
                f"Subscription {subscription.number} renewed until {subscription.expiry_date}.",
            )

        else:
            messages.error(request, f"Unknown lifecycle action '{action}'.")

    except ValidationError as exc:
        messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
    except ValueError as exc:
        messages.error(request, f"Invalid input: {exc}")

    return redirect("subscriptions:subscription_detail", pk=subscription.pk)
