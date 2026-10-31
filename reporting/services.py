"""Reporting and financial analytics services.

Reconciles financial metrics across subscriptions, invoices, and payments
according to the approved financial proposal (docs/contracts/financial-proposal.md):
- Invoiced Net Sales: excludes tax (net_total = subtotal - discount_total)
- Collected Cash: sum of settled payment records
- Outstanding: sum of unpaid balances on confirmed invoices
- Overdue: sum of unpaid balances past due date
- Active Subscriptions: consumes canonical definition (status=ACTIVE, is_paused=False)
"""

import datetime
from decimal import Decimal
from typing import Any

from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from billing.models import Invoice
from payments.models import Payment
from plans.models import Plan
from subscriptions.models import Subscription


def get_financial_dashboard_metrics(
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
    as_of_date: datetime.date | None = None,
) -> dict[str, Any]:
    """Calculate executive financial totals, reconciling with underlying records.

    Parameters
    ----------
    start_date:
        Optional start boundary for invoice issuance and payment receipt.
    end_date:
        Optional end boundary for invoice issuance and payment receipt.
    as_of_date:
        Target date for aging/overdue checks; defaults to today.

    Returns
    -------
    dict
        Structured financial breakdown containing:
        - invoiced_net_sales (excluding tax)
        - invoiced_gross_sales (subtotal)
        - invoiced_tax_total
        - invoiced_total (gross - discount + tax)
        - invoice_counts by status
        - collected_cash (total settled payments)
        - payment_method_breakdown
        - outstanding_receivables (unsettled balance on confirmed invoices)
        - overdue_receivables (unsettled balance past due_date)
        - overdue_invoice_count
        - subscription_counts (active, paused, quotation, draft, closed)
        - plan_breakdown
    """
    if as_of_date is None:
        as_of_date = timezone.localdate()

    # ── 1. Invoice Inquiries ──────────────────────────────────────────────────
    invoice_qs = Invoice.objects.exclude(status=Invoice.Status.CANCELLED)

    if start_date is not None:
        invoice_qs = invoice_qs.filter(issue_date__gte=start_date)
    if end_date is not None:
        invoice_qs = invoice_qs.filter(issue_date__lte=end_date)

    inv_agg = invoice_qs.aggregate(
        net_sales=Sum("net_total"),
        gross_sales=Sum("subtotal"),
        discount_total=Sum("discount_total"),
        tax_total=Sum("tax_total"),
        total=Sum("total"),
        count=Count("id"),
    )

    invoiced_net_sales = inv_agg["net_sales"] or Decimal("0.00")
    invoiced_gross_sales = inv_agg["gross_sales"] or Decimal("0.00")
    invoiced_discount_total = inv_agg["discount_total"] or Decimal("0.00")
    invoiced_tax_total = inv_agg["tax_total"] or Decimal("0.00")
    invoiced_total = inv_agg["total"] or Decimal("0.00")
    invoices_issued_count = inv_agg["count"] or 0

    # Status counts across all invoices (or filtered range)
    status_counts_raw = (
        Invoice.objects.filter(
            issue_date__gte=start_date if start_date else datetime.date.min,
            issue_date__lte=end_date if end_date else datetime.date.max,
        )
        .values("status")
        .annotate(count=Count("id"))
    )
    invoice_status_counts = {item["status"]: item["count"] for item in status_counts_raw}

    # ── 2. Collected Cash (Payments) ──────────────────────────────────────────
    payment_qs = Payment.objects.all()
    if start_date is not None:
        payment_qs = payment_qs.filter(paid_at__date__gte=start_date)
    if end_date is not None:
        payment_qs = payment_qs.filter(paid_at__date__lte=end_date)

    collected_cash = payment_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    payments_count = payment_qs.count()

    method_agg = (
        payment_qs.values("method")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    payment_method_breakdown = [
        {
            "method": item["method"],
            "method_display": dict(Payment.Method.choices).get(item["method"], item["method"]),
            "total": item["total"] or Decimal("0.00"),
            "count": item["count"],
        }
        for item in method_agg
    ]

    # ── 3. Receivables & Aging (Outstanding & Overdue) ────────────────────────
    # Outstanding = Confirmed invoices where amount_paid < total
    confirmed_invoices = Invoice.objects.filter(
        status=Invoice.Status.CONFIRMED,
        amount_paid__lt=F("total"),
    )

    outstanding_agg = confirmed_invoices.aggregate(
        total_invoiced=Sum("total"),
        total_paid=Sum("amount_paid"),
        count=Count("id"),
    )
    outstanding_invoiced = outstanding_agg["total_invoiced"] or Decimal("0.00")
    outstanding_paid = outstanding_agg["total_paid"] or Decimal("0.00")
    outstanding_receivables = max(Decimal("0.00"), outstanding_invoiced - outstanding_paid)
    outstanding_count = outstanding_agg["count"] or 0

    # Overdue = Confirmed invoices where amount_paid < total and due_date < as_of_date
    overdue_invoices = confirmed_invoices.filter(due_date__lt=as_of_date)
    overdue_agg = overdue_invoices.aggregate(
        total_invoiced=Sum("total"),
        total_paid=Sum("amount_paid"),
        count=Count("id"),
    )
    overdue_invoiced = overdue_agg["total_invoiced"] or Decimal("0.00")
    overdue_paid = overdue_agg["total_paid"] or Decimal("0.00")
    overdue_receivables = max(Decimal("0.00"), overdue_invoiced - overdue_paid)
    overdue_count = overdue_agg["count"] or 0

    # ── 4. Subscription Health Metrics ────────────────────────────────────────
    # Standard: active count strictly excludes pauses (financial-proposal.md)
    sub_counts_raw = Subscription.objects.values("status", "is_paused").annotate(count=Count("id"))
    active_paying_count = 0
    paused_count = 0
    quotation_count = 0
    draft_count = 0
    closed_count = 0

    for item in sub_counts_raw:
        st = item["status"]
        is_p = item["is_paused"]
        cnt = item["count"]
        if st == Subscription.Status.ACTIVE:
            if is_p:
                paused_count += cnt
            else:
                active_paying_count += cnt
        elif st == Subscription.Status.QUOTATION:
            quotation_count += cnt
        elif st == Subscription.Status.DRAFT:
            draft_count += cnt
        elif st == Subscription.Status.CLOSED:
            closed_count += cnt

    total_subscriptions_count = (
        active_paying_count + paused_count + quotation_count + draft_count + closed_count
    )

    # ── 5. Plan Distribution & Breakdown ──────────────────────────────────────
    plans = Plan.objects.annotate(
        total_subs=Count("subscriptions"),
        active_subs=Count(
            "subscriptions",
            filter=Q(
                subscriptions__status=Subscription.Status.ACTIVE,
                subscriptions__is_paused=False,
            ),
        ),
        paused_subs=Count(
            "subscriptions",
            filter=Q(
                subscriptions__status=Subscription.Status.ACTIVE,
                subscriptions__is_paused=True,
            ),
        ),
    ).order_by("name")

    plan_breakdown = []
    for plan in plans:
        # Reconcile billed revenue for subscriptions under this plan
        plan_inv_total = Invoice.objects.filter(
            subscription__plan=plan,
            status__in=[Invoice.Status.CONFIRMED, Invoice.Status.PAID],
        ).aggregate(net=Sum("net_total"))["net"] or Decimal("0.00")
        plan_breakdown.append(
            {
                "plan_id": plan.id,
                "plan_name": plan.name,
                "billing_interval": plan.get_interval_display(),
                "base_price": plan.price,
                "total_subs": plan.total_subs,
                "active_subs": plan.active_subs,
                "paused_subs": plan.paused_subs,
                "invoiced_net": plan_inv_total,
            }
        )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "as_of_date": as_of_date,
        # Sales metrics (ex-tax sales vs gross vs total)
        "invoiced_net_sales": invoiced_net_sales,
        "invoiced_gross_sales": invoiced_gross_sales,
        "invoiced_discount_total": invoiced_discount_total,
        "invoiced_tax_total": invoiced_tax_total,
        "invoiced_total": invoiced_total,
        "invoices_issued_count": invoices_issued_count,
        "invoice_status_counts": invoice_status_counts,
        # Cash collections
        "collected_cash": collected_cash,
        "payments_count": payments_count,
        "payment_method_breakdown": payment_method_breakdown,
        # Receivables & Aging
        "outstanding_receivables": outstanding_receivables,
        "outstanding_count": outstanding_count,
        "overdue_receivables": overdue_receivables,
        "overdue_count": overdue_count,
        # Subscriptions health
        "active_paying_count": active_paying_count,
        "paused_count": paused_count,
        "quotation_count": quotation_count,
        "draft_count": draft_count,
        "closed_count": closed_count,
        "total_subscriptions_count": total_subscriptions_count,
        # Plans
        "plan_breakdown": plan_breakdown,
    }
