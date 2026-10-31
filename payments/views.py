import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import User
from accounts.permissions import require_roles, scope_to_customer
from billing.models import Invoice

from .forms import PaymentForm
from .models import Payment
from .services import (
    InvalidPaymentError,
    OverpaymentError,
    PaymentConflictError,
    record_payment,
)


@login_required
def payment_list(request):
    """Staff and Admin view of all settled payments with filters."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)

    queryset = Payment.objects.select_related("invoice", "customer").all()

    method_filter = request.GET.get("method", "").strip().upper()
    if method_filter in Payment.Method.values:
        queryset = queryset.filter(method=method_filter)

    search = request.GET.get("q", "").strip()
    if search:
        queryset = (
            queryset.filter(invoice__number__icontains=search)
            | queryset.filter(customer__email__icontains=search)
            | queryset.filter(transaction_ref__icontains=search)
        )

    total_collected = queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    return render(
        request,
        "payments/payment_list.html",
        {
            "payments": queryset,
            "method_filter": method_filter,
            "search_query": search,
            "method_choices": Payment.Method.choices,
            "total_collected": total_collected,
        },
    )


@require_http_methods(["GET", "POST"])
def payment_create(request, invoice_pk):
    """Staff action to record a payment against an invoice."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)
    invoice = get_object_or_404(Invoice, pk=invoice_pk)

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            method = form.cleaned_data["method"]
            amount = form.cleaned_data["amount"]
            transaction_ref = form.cleaned_data.get("transaction_ref") or ""
            notes = form.cleaned_data.get("notes") or ""
            idempotency_key = form.cleaned_data.get("idempotency_key")
            if not idempotency_key:
                idempotency_key = str(uuid.uuid4())
            else:
                idempotency_key = str(idempotency_key)

            try:
                payment = record_payment(
                    invoice=invoice,
                    amount=amount,
                    method=method,
                    idempotency_key=idempotency_key,
                    transaction_ref=transaction_ref,
                    notes=notes,
                )
                messages.success(
                    request,
                    f"Payment of ₹{payment.amount} recorded for {invoice.number} via {payment.get_method_display()}.",
                )
            except OverpaymentError as exc:
                messages.error(request, str(exc))
            except PaymentConflictError as exc:
                messages.error(request, str(exc))
            except InvalidPaymentError as exc:
                messages.error(request, str(exc))
        else:
            errors = " ".join([f"{f}: {e[0]}" for f, e in form.errors.items()])
            messages.error(request, f"Could not record payment. {errors}")

    return redirect("billing:invoice_detail", pk=invoice.pk)


@require_POST
def customer_payment_create(request, invoice_pk):
    """Customer self-service payment recording/simulation on their own confirmed invoice."""
    invoice = get_object_or_404(
        scope_to_customer(Invoice.objects.all(), request.user, "customer"),
        pk=invoice_pk,
    )

    if invoice.status != Invoice.Status.CONFIRMED:
        messages.error(
            request,
            f"Invoice {invoice.number} is not awaiting payment.",
        )
        return redirect("billing:customer_invoice_detail", pk=invoice.pk)

    amount_raw = request.POST.get("amount", "").strip()
    if amount_raw:
        try:
            amount = Decimal(amount_raw)
        except InvalidOperation:
            messages.error(request, "Invalid payment amount.")
            return redirect("billing:customer_invoice_detail", pk=invoice.pk)
    else:
        amount = invoice.amount_due

    method = request.POST.get("method", Payment.Method.SIMULATED).strip().upper()
    if method not in Payment.Method.values:
        method = Payment.Method.SIMULATED

    idempotency_key = request.POST.get("idempotency_key", "").strip()
    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())

    transaction_ref = request.POST.get("transaction_ref", "").strip()
    if not transaction_ref:
        transaction_ref = f"SIM-{uuid.uuid4().hex[:8].upper()}"

    try:
        payment = record_payment(
            invoice=invoice,
            amount=amount,
            method=method,
            idempotency_key=idempotency_key,
            transaction_ref=transaction_ref,
            notes="Customer self-service payment",
        )
        messages.success(
            request,
            f"Payment of ₹{payment.amount} successful! Ref: {payment.transaction_ref}",
        )
    except (OverpaymentError, PaymentConflictError, InvalidPaymentError) as exc:
        messages.error(request, str(exc))

    return redirect("billing:customer_invoice_detail", pk=invoice.pk)
