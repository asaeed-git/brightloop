"""Exact, side-effect-free pricing for quotations and invoice snapshots.

Amounts become integer minor units before arithmetic. Fraction preserves percentage
precision without depending on the process-wide Decimal rounding context.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Literal


class PricingError(ValueError):
    """Invalid financial input; map to the calling form/API's validation errors."""


@dataclass(frozen=True)
class Discount:
    rule_id: str
    kind: Literal["FIXED", "PERCENTAGE"]
    value: Decimal
    scope: Literal["SUBSCRIPTION", "PRODUCT"] = "SUBSCRIPTION"
    product_id: str | None = None


@dataclass(frozen=True)
class Charge:
    charge_id: str
    quantity: int
    unit_price: Decimal
    variant_adjustment: Decimal = Decimal("0.00")
    tax_rate: Decimal = Decimal("0")
    product_id: str | None = None
    discount: Discount | None = None


@dataclass(frozen=True)
class LineTotal:
    charge_id: str
    gross: Decimal
    discount: Decimal
    net: Decimal
    tax: Decimal
    total: Decimal
    discount_rule_id: str | None


@dataclass(frozen=True)
class PriceTotal:
    currency: str
    lines: tuple[LineTotal, ...]
    subtotal: Decimal
    discount: Decimal
    net: Decimal
    tax: Decimal
    total: Decimal


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise PricingError(f"{label} must be a nonempty string.")


def _decimal(value, label):
    if not isinstance(value, Decimal) or not value.is_finite():
        raise PricingError(f"{label} must be a finite Decimal, never a float.")
    return Fraction(value)


def _cents(value, label, *, signed=False):
    cents = _decimal(value, label) * 100
    if cents.denominator != 1 or (cents < 0 and not signed):
        raise PricingError(f"{label} must have cent precision and an allowed sign.")
    return cents.numerator


def _rate(value, label):
    rate = _decimal(value, label)
    if not 0 <= rate <= 100:
        raise PricingError(f"{label} must be between 0 and 100.")
    return rate / 100


def _round_half_up(value):
    whole, remainder = divmod(value.numerator, value.denominator)
    return whole + (2 * remainder >= value.denominator)


def _money(cents):
    # Construct from text rather than Decimal division, which can inherit a caller's
    # low precision and silently round a correctly calculated large result.
    return Decimal(f"{cents // 100}.{cents % 100:02d}")


def _validate_discount(rule):
    if not isinstance(rule, Discount):
        raise PricingError("Each charge accepts one Discount or None.")
    _identifier(rule.rule_id, "Discount rule ID")
    if rule.kind == "FIXED":
        _cents(rule.value, "Fixed discount")
    elif rule.kind == "PERCENTAGE":
        _rate(rule.value, "Discount percentage")
    else:
        raise PricingError("Discount kind must be FIXED or PERCENTAGE.")
    if rule.scope == "PRODUCT":
        _identifier(rule.product_id, "Discount product ID")
    elif rule.scope != "SUBSCRIPTION" or rule.product_id is not None:
        raise PricingError("Subscription discounts cannot specify a product ID.")


def calculate_price(charges, *, currency="INR") -> PriceTotal:
    """Calculate already-selected eligible charges; never reserve discount usage.

    Each fixed rule is applied once across its selected matching charges. Caller services
    must load trusted prices and validate dates, thresholds, usage availability and plan
    quantity rules. This function validates shape, scope, arithmetic and consistency.
    An empty charge sequence is a zero preview; invoice issuance must require service lines.
    """
    if currency != "INR":
        raise PricingError("Only the agreed INR currency is supported.")
    try:
        charges = tuple(charges)
    except TypeError as exc:
        raise PricingError("Charges must be an iterable of Charge values.") from exc
    seen = set()
    gross = []
    rates = []
    rules = {}
    groups = defaultdict(list)
    for index, charge in enumerate(charges):
        if not isinstance(charge, Charge):
            raise PricingError("Each line must be a Charge.")
        _identifier(charge.charge_id, "Charge ID")
        if charge.charge_id in seen:
            raise PricingError("Charge IDs must be unique.")
        seen.add(charge.charge_id)
        if type(charge.quantity) is not int or charge.quantity <= 0:
            raise PricingError("Quantity must be a positive whole number.")
        if charge.product_id is not None:
            _identifier(charge.product_id, "Product ID")
        unit = _cents(charge.unit_price, "Unit price")
        extra = _cents(charge.variant_adjustment, "Variant adjustment", signed=True)
        if unit + extra < 0:
            raise PricingError("Effective unit price cannot be negative.")
        gross.append((unit + extra) * charge.quantity)
        rates.append(_rate(charge.tax_rate, "Tax rate"))
        rule = charge.discount
        if rule is not None:
            _validate_discount(rule)
            if rule.scope == "PRODUCT" and rule.product_id != charge.product_id:
                raise PricingError("Product discount does not match this charge.")
            if rule.rule_id in rules and rules[rule.rule_id] != rule:
                raise PricingError("A discount rule ID must have one consistent definition.")
            rules[rule.rule_id] = rule
            groups[rule.rule_id].append(index)

    discounts = [0] * len(charges)
    for rule_id, indexes in groups.items():
        rule = rules[rule_id]
        if rule.kind == "PERCENTAGE":
            rate = _rate(rule.value, "Discount percentage")
            for index in indexes:
                discounts[index] = min(gross[index], _round_half_up(gross[index] * rate))
            continue
        eligible_gross = sum(gross[index] for index in indexes)
        budget = min(_cents(rule.value, "Fixed discount"), eligible_gross)
        if not eligible_gross or not budget:
            continue
        for index in indexes:
            discounts[index] = budget * gross[index] // eligible_gross
        remainder = budget - sum(discounts[index] for index in indexes)
        ranked = sorted(
            indexes,
            key=lambda index: (
                -(budget * gross[index] % eligible_gross),
                charges[index].charge_id,
            ),
        )
        for index in ranked[:remainder]:
            discounts[index] += 1

    lines = []
    taxes = []
    for index, charge in enumerate(charges):
        net = gross[index] - discounts[index]
        tax = _round_half_up(net * rates[index])
        taxes.append(tax)
        lines.append(
            LineTotal(
                charge.charge_id,
                _money(gross[index]),
                _money(discounts[index]),
                _money(net),
                _money(tax),
                _money(net + tax),
                charge.discount.rule_id if charge.discount is not None else None,
            )
        )
    subtotal = sum(gross)
    discount = sum(discounts)
    net = subtotal - discount
    tax = sum(taxes)
    return PriceTotal(
        currency,
        tuple(lines),
        _money(subtotal),
        _money(discount),
        _money(net),
        _money(tax),
        _money(net + tax),
    )
