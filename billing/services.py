import datetime
import logging
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from billing.models import BillingRunRecord, Invoice, InvoiceLine
from pricing.services import Charge, Discount, calculate_price
from subscriptions.models import Subscription, compute_next_period_end

logger = logging.getLogger(__name__)


class DuplicateBillingError(Exception):
    """Raised when an invoice has already been issued for the same subscription period."""


@dataclass
class BillingResult:
    subscriptions_checked: int
    invoices_created: int
    total_billed_amount: Decimal
    invoices: list[Invoice]
    errors: list[str]


def generate_invoice_for_subscription(
    subscription: Subscription,
    target_date: datetime.date | None = None,
) -> Invoice:
    """Generate an authoritative, immutable invoice for an active subscription period.

    Ensures transactional safety, anti-duplication, exact cent arithmetic via B2 calculator,
    and frozen line-item pricing snapshots.
    """
    if subscription.status != Subscription.Status.ACTIVE:
        raise ValidationError(
            f"Cannot bill subscription {subscription.number}: status is {subscription.get_status_display()}."
        )

    if subscription.is_paused:
        raise ValidationError(
            f"Cannot bill subscription {subscription.number}: service is currently paused."
        )

    period_start = subscription.current_period_start
    period_end = subscription.current_period_end

    if not period_start or not period_end:
        raise ValidationError(
            f"Subscription {subscription.number} has undefined billing period boundaries."
        )

    # Database-level and service-level anti-duplication check
    if Invoice.objects.filter(subscription=subscription, period_start=period_start).exists():
        raise DuplicateBillingError(
            f"An invoice for subscription {subscription.number} covering period {period_start} has already been issued."
        )

    today = target_date or timezone.localdate()
    issue_date = today
    due_date = issue_date + datetime.timedelta(days=subscription.payment_terms_days)

    # 1. Build calculation charges
    charges = []
    tax_rate = (
        subscription.tax_rate.rate
        if subscription.tax_rate and subscription.tax_rate.is_active
        else Decimal("0.00")
    )

    # Base plan fee line
    if subscription.base_price > Decimal("0.00"):
        charges.append(
            Charge(
                charge_id=f"plan_{subscription.id}",
                quantity=1,
                unit_price=subscription.base_price,
                variant_adjustment=Decimal("0.00"),
                tax_rate=tax_rate,
            )
        )

    # Product lines
    sub_lines = list(subscription.lines.select_related("product", "variant").all())
    for line in sub_lines:
        extra = line.variant.price_extra if line.variant else Decimal("0.00")
        base_unit = line.unit_price - extra if line.variant else line.product.sales_price
        if base_unit < Decimal("0.00"):
            base_unit = line.unit_price
            extra = Decimal("0.00")

        charges.append(
            Charge(
                charge_id=f"line_{line.id}",
                quantity=line.quantity,
                unit_price=base_unit,
                variant_adjustment=extra,
                tax_rate=tax_rate,
                product_id=str(line.product.id),
            )
        )

    # Evaluate eligible discount rule
    selected_rule = subscription.discount_rule
    if selected_rule and selected_rule.is_active:
        is_date_valid = True
        if selected_rule.valid_from and issue_date < selected_rule.valid_from:
            is_date_valid = False
        if selected_rule.valid_until and issue_date > selected_rule.valid_until:
            is_date_valid = False

        if is_date_valid:
            eligible_gross = sum(
                (c.unit_price + c.variant_adjustment) * c.quantity
                for c in charges
                if selected_rule.scope == "SUBSCRIPTION" or selected_rule.product_id == c.product_id
            )
            threshold_met = (
                not selected_rule.min_eligible_gross
                or eligible_gross >= selected_rule.min_eligible_gross
            )

            # Check usage limit
            usage_available = True
            if selected_rule.max_uses:
                used_count = InvoiceLine.objects.filter(discount_rule=selected_rule).count()
                if used_count >= selected_rule.max_uses:
                    usage_available = False

            if threshold_met and usage_available:
                rule_spec = Discount(
                    rule_id=str(selected_rule.id),
                    kind=selected_rule.kind,
                    value=selected_rule.value,
                    scope=selected_rule.scope,
                    product_id=str(selected_rule.product_id) if selected_rule.product_id else None,
                )
                updated_charges = []
                for c in charges:
                    if selected_rule.scope == "SUBSCRIPTION" or (
                        selected_rule.scope == "PRODUCT"
                        and selected_rule.product_id == c.product_id
                    ):
                        updated_charges.append(
                            Charge(
                                charge_id=c.charge_id,
                                quantity=c.quantity,
                                unit_price=c.unit_price,
                                variant_adjustment=c.variant_adjustment,
                                tax_rate=c.tax_rate,
                                product_id=c.product_id,
                                discount=rule_spec,
                            )
                        )
                    else:
                        updated_charges.append(c)
                charges = updated_charges
            else:
                selected_rule = None
        else:
            selected_rule = None
    else:
        selected_rule = None

    if not charges:
        raise ValidationError("Cannot create invoice: no billable charges found.")

    price_total = calculate_price(charges)

    # 2. Persist invoice and snapshot lines atomically
    with transaction.atomic():
        invoice = Invoice.objects.create(
            customer=subscription.customer,
            subscription=subscription,
            status=Invoice.Status.CONFIRMED,
            period_start=period_start,
            period_end=period_end,
            issue_date=issue_date,
            due_date=due_date,
            currency="INR",
            subtotal=price_total.subtotal,
            discount_total=price_total.discount,
            net_total=price_total.net,
            tax_total=price_total.tax,
            total=price_total.total,
            notes=f"Recurring billing for {subscription.number} [{subscription.plan.name}].",
        )

        line_totals_map = {lt.charge_id: lt for lt in price_total.lines}

        # Create base fee line snapshot
        if subscription.base_price > Decimal("0.00"):
            plan_charge_id = f"plan_{subscription.id}"
            lt = line_totals_map.get(plan_charge_id)
            if lt:
                InvoiceLine.objects.create(
                    invoice=invoice,
                    description=f"Base Plan: {subscription.plan.name}",
                    quantity=1,
                    unit_price=subscription.base_price,
                    gross=lt.gross,
                    discount=lt.discount,
                    net=lt.net,
                    tax=lt.tax,
                    total=lt.total,
                    discount_rule=selected_rule if lt.discount_rule_id else None,
                )

        # Create product lines snapshots
        for line in sub_lines:
            line_charge_id = f"line_{line.id}"
            lt = line_totals_map.get(line_charge_id)
            if lt:
                desc = (
                    f"{line.product.name} ({line.variant.name})"
                    if line.variant
                    else line.product.name
                )
                InvoiceLine.objects.create(
                    invoice=invoice,
                    product=line.product,
                    variant=line.variant,
                    description=desc,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    gross=lt.gross,
                    discount=lt.discount,
                    net=lt.net,
                    tax=lt.tax,
                    total=lt.total,
                    discount_rule=selected_rule if lt.discount_rule_id else None,
                )

    return invoice


def advance_subscription_period(
    subscription: Subscription,
    target_date: datetime.date | None = None,
) -> None:
    """Advance subscription period start, end, and next_billing_date to the next cycle.

    Enforces contract expiry rules (auto-closing on expiry or ending scheduling).
    """
    next_start = subscription.current_period_end

    # Contract expiry reached
    if subscription.expiry_date and next_start >= subscription.expiry_date:
        if subscription.auto_close_on_expiry:
            subscription.status = Subscription.Status.CLOSED
            subscription.close_date = next_start
            subscription.close_reason = "Contract term completed."
            subscription.next_billing_date = None
        else:
            # Active without further recurring schedule
            subscription.next_billing_date = None
    else:
        # Compute next period end
        next_end = compute_next_period_end(
            next_start, subscription.plan.interval, subscription.expiry_date
        )
        subscription.current_period_start = next_start
        subscription.current_period_end = next_end
        # Upfront billing: next billing occurs on next_start
        subscription.next_billing_date = next_start

    subscription.save()


def run_recurring_billing(
    target_date: datetime.date | None = None,
    executed_by=None,
) -> BillingRunRecord:
    """Execute the recurring billing engine.

    Queries all ACTIVE, unpaused subscriptions where next_billing_date <= target_date.
    Each subscription is billed and advanced atomically. Failures are isolated per subscription.
    Audit log record is persisted and returned.
    """
    today = target_date or timezone.localdate()

    eligible_subs = (
        Subscription.objects.filter(
            status=Subscription.Status.ACTIVE,
            is_paused=False,
            next_billing_date__lte=today,
        )
        .select_related("customer", "plan", "tax_rate", "discount_rule")
        .prefetch_related("lines__product", "lines__variant")
        .order_by("number")
    )

    checked_count = eligible_subs.count()
    invoices_created = 0
    total_billed = Decimal("0.00")
    log_messages = []
    overall_success = True

    for sub in eligible_subs:
        try:
            with transaction.atomic():
                invoice = generate_invoice_for_subscription(sub, target_date=today)
                advance_subscription_period(sub, target_date=today)
                invoices_created += 1
                total_billed += invoice.total
                log_messages.append(
                    f"OK: Subscription {sub.number} billed {invoice.number} for ₹{invoice.total}."
                )
        except DuplicateBillingError as exc:
            logger.warning("Duplicate billing skipped for %s: %s", sub.number, exc)
            log_messages.append(f"SKIPPED: {sub.number} already billed for current period.")
        except Exception as exc:
            overall_success = False
            logger.exception("Error processing billing for subscription %s: %s", sub.number, exc)
            log_messages.append(f"ERROR: {sub.number} failed: {exc}")

    record = BillingRunRecord.objects.create(
        run_date=today,
        executed_by=executed_by,
        subscriptions_checked=checked_count,
        invoices_created=invoices_created,
        total_billed_amount=total_billed,
        success=overall_success,
        log_summary="\n".join(log_messages),
    )

    return record
