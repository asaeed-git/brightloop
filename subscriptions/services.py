import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from pricing.services import Charge, Discount, PriceTotal, calculate_price
from subscriptions.models import (
    Subscription,
    SubscriptionLine,
    compute_next_period_end,
)


def validate_subscription_lines(subscription: Subscription) -> None:
    lines = list(subscription.lines.all())
    if not lines:
        raise ValidationError("Subscription must contain at least one product line item.")

    total_seats = sum(line.quantity for line in lines)
    if total_seats < subscription.plan.min_quantity:
        raise ValidationError(
            f"Total quantity ({total_seats}) is less than plan minimum required"
            f" quantity ({subscription.plan.min_quantity})."
        )


def transition_to_quotation(
    subscription: Subscription, validity_days: int | None = None
) -> Subscription:
    if subscription.status not in [
        Subscription.Status.DRAFT,
        Subscription.Status.QUOTATION,
    ]:
        raise ValidationError(
            f"Cannot issue quotation from status '{subscription.get_status_display()}'."
        )

    validate_subscription_lines(subscription)

    today = timezone.localdate()
    subscription.status = Subscription.Status.QUOTATION
    subscription.quotation_date = today

    if validity_days is not None:
        if validity_days < 1:
            raise ValidationError("Quotation validity must be at least 1 day.")
        subscription.quotation_valid_until = today + datetime.timedelta(days=validity_days)
    elif not subscription.quotation_valid_until:
        subscription.quotation_valid_until = today + datetime.timedelta(days=30)

    subscription.save()
    return subscription


def transition_to_confirmed(subscription: Subscription, confirmed_by=None) -> Subscription:
    if subscription.status not in [
        Subscription.Status.QUOTATION,
        Subscription.Status.DRAFT,
    ]:
        raise ValidationError(
            f"Cannot confirm subscription from status '{subscription.get_status_display()}'."
        )

    if subscription.status == Subscription.Status.QUOTATION and subscription.is_quotation_expired:
        raise ValidationError(
            f"Cannot confirm: quotation expired on"
            f" {subscription.quotation_valid_until}. Please extend validity"
            " before confirming."
        )

    validate_subscription_lines(subscription)

    subscription.status = Subscription.Status.CONFIRMED
    subscription.save()
    return subscription


def transition_to_active(
    subscription: Subscription, start_date: datetime.date | None = None
) -> Subscription:
    if subscription.status != Subscription.Status.CONFIRMED:
        raise ValidationError(
            f"Cannot activate subscription from status '{subscription.get_status_display()}'. Must be Confirmed."
        )

    validate_subscription_lines(subscription)

    today = timezone.localdate()
    start = start_date or subscription.start_date or today

    if subscription.expiry_date and start >= subscription.expiry_date:
        raise ValidationError(
            "Cannot activate subscription: start date is at or after contract expiry date."
        )

    subscription.start_date = start
    subscription.current_period_start = start
    subscription.current_period_end = compute_next_period_end(
        start, subscription.plan.interval, subscription.expiry_date
    )
    # Upfront billing: next billing date is start of period
    subscription.next_billing_date = start
    subscription.status = Subscription.Status.ACTIVE
    subscription.is_paused = False
    subscription.save()
    return subscription


def pause_subscription(subscription: Subscription, reason: str = "") -> Subscription:
    if subscription.status != Subscription.Status.ACTIVE:
        raise ValidationError("Only active subscriptions can be paused.")

    if subscription.is_paused:
        raise ValidationError("Subscription is already paused.")

    if not subscription.can_pause:
        raise ValidationError("This subscription's plan terms do not permit pausing.")

    subscription.is_paused = True
    subscription.pause_date = timezone.localdate()
    subscription.pause_reason = reason.strip()
    subscription.save()
    return subscription


def resume_subscription(subscription: Subscription) -> Subscription:
    if subscription.status != Subscription.Status.ACTIVE:
        raise ValidationError("Only active subscriptions can be resumed.")

    if not subscription.is_paused:
        raise ValidationError("Subscription is not currently paused.")

    subscription.is_paused = False
    subscription.pause_date = None
    subscription.pause_reason = ""
    subscription.save()
    return subscription


def close_subscription(subscription: Subscription, reason: str = "") -> Subscription:
    if subscription.status == Subscription.Status.CLOSED:
        raise ValidationError("Subscription is already closed.")

    today = timezone.localdate()
    if subscription.status == Subscription.Status.ACTIVE:
        if (
            not subscription.can_early_close
            and subscription.expiry_date
            and today < subscription.expiry_date
        ):
            raise ValidationError(
                "This subscription does not allow early closure before its"
                f" expiry date ({subscription.expiry_date})."
            )

    subscription.status = Subscription.Status.CLOSED
    subscription.close_date = today
    subscription.close_reason = reason.strip()
    subscription.save()
    return subscription


def renew_subscription(subscription: Subscription, new_expiry_date: datetime.date) -> Subscription:
    if not subscription.can_renew:
        raise ValidationError("This subscription does not permit contract renewal.")

    today = timezone.localdate()
    if new_expiry_date <= today:
        raise ValidationError("New expiry date must be in the future.")

    if subscription.expiry_date and new_expiry_date <= subscription.expiry_date:
        raise ValidationError(
            f"New expiry date must follow current expiry date ({subscription.expiry_date})."
        )

    subscription.expiry_date = new_expiry_date
    if subscription.status == Subscription.Status.CLOSED:
        subscription.status = Subscription.Status.ACTIVE
        subscription.close_date = None
        subscription.close_reason = ""

    subscription.save()
    return subscription


def create_subscription_from_template(
    template,
    customer,
    start_date: datetime.date | None = None,
    notes: str = "",
) -> Subscription:
    today = timezone.localdate()
    with transaction.atomic():
        subscription = Subscription.objects.create(
            customer=customer,
            plan=template.plan,
            base_price=template.plan.price,
            can_pause=template.plan.can_pause,
            can_early_close=template.plan.can_early_close,
            auto_close_on_expiry=template.plan.auto_close_on_expiry,
            can_renew=template.plan.can_renew,
            payment_terms_days=15,
            status=Subscription.Status.QUOTATION,
            start_date=start_date or today,
            quotation_date=today,
            quotation_valid_until=today + datetime.timedelta(days=template.validity_days),
            notes=notes or template.notes,
        )

        for line in template.lines.select_related("product", "variant").all():
            price = line.variant.effective_sales_price if line.variant else line.product.sales_price
            SubscriptionLine.objects.create(
                subscription=subscription,
                product=line.product,
                variant=line.variant,
                quantity=line.quantity,
                unit_price=price,
            )

        return subscription


def calculate_subscription_pricing(
    subscription: Subscription,
) -> PriceTotal | None:
    lines = list(subscription.lines.select_related("product", "variant").all())
    if not lines and subscription.base_price <= Decimal("0.00"):
        return None

    charges = []
    tax_rate = (
        subscription.tax_rate.rate
        if subscription.tax_rate and subscription.tax_rate.is_active
        else Decimal("0.00")
    )

    # 1. Base plan fee charge
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

    # 2. Product line charges
    for line in lines:
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

    # 3. Attach eligible discount rule if configured
    rule = subscription.discount_rule
    if rule and rule.is_active:
        today = timezone.localdate()
        valid_date = True
        if rule.valid_from and today < rule.valid_from:
            valid_date = False
        if rule.valid_until and today > rule.valid_until:
            valid_date = False

        if valid_date:
            gross_sum = sum(
                (c.unit_price + c.variant_adjustment) * c.quantity
                for c in charges
                if rule.scope == "SUBSCRIPTION" or rule.product_id == c.product_id
            )
            if not rule.min_eligible_gross or gross_sum >= rule.min_eligible_gross:
                discount_spec = Discount(
                    rule_id=str(rule.id),
                    kind=rule.kind,
                    value=rule.value,
                    scope=rule.scope,
                    product_id=str(rule.product_id) if rule.product_id else None,
                )
                updated_charges = []
                for c in charges:
                    if rule.scope == "SUBSCRIPTION" or (
                        rule.scope == "PRODUCT" and rule.product_id == c.product_id
                    ):
                        updated_charges.append(
                            Charge(
                                charge_id=c.charge_id,
                                quantity=c.quantity,
                                unit_price=c.unit_price,
                                variant_adjustment=c.variant_adjustment,
                                tax_rate=c.tax_rate,
                                product_id=c.product_id,
                                discount=discount_spec,
                            )
                        )
                    else:
                        updated_charges.append(c)
                charges = updated_charges

    return calculate_price(charges) if charges else None
