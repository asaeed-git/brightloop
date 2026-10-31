import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from accounts.models import User
from accounts.permissions import require_roles
from billing.models import Invoice
from payments.models import Payment

from .services import get_financial_dashboard_metrics


@login_required
def dashboard(request):
    """Staff and Admin Executive Financial & Operational Dashboard."""
    require_roles(request.user, User.Role.ADMIN, User.Role.STAFF)

    preset = request.GET.get("preset", "30d").lower()
    today = timezone.localdate()

    start_date = None
    end_date = None

    if preset == "7d":
        start_date = today - datetime.timedelta(days=7)
        end_date = today
    elif preset == "30d":
        start_date = today - datetime.timedelta(days=30)
        end_date = today
    elif preset == "month":
        start_date = today.replace(day=1)
        end_date = today
    elif preset == "all":
        start_date = None
        end_date = None
    elif preset == "custom":
        start_str = request.GET.get("start_date", "").strip()
        end_str = request.GET.get("end_date", "").strip()
        if start_str:
            try:
                start_date = datetime.date.fromisoformat(start_str)
            except ValueError:
                start_date = None
        if end_str:
            try:
                end_date = datetime.date.fromisoformat(end_str)
            except ValueError:
                end_date = None

    metrics = get_financial_dashboard_metrics(
        start_date=start_date,
        end_date=end_date,
        as_of_date=today,
    )

    # Recent activity drill-downs for staff convenience
    recent_invoices = Invoice.objects.select_related("customer", "subscription").order_by(
        "-issue_date", "-created_at"
    )[:6]
    recent_payments = Payment.objects.select_related("invoice", "customer").order_by(
        "-paid_at", "-created_at"
    )[:6]

    context = {
        "metrics": metrics,
        "preset": preset,
        "start_date": start_date,
        "end_date": end_date,
        "today": today,
        "recent_invoices": recent_invoices,
        "recent_payments": recent_payments,
    }
    return render(request, "reporting/dashboard.html", context)
