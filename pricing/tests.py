from dataclasses import replace
from decimal import Decimal, localcontext
from itertools import permutations

from django.test import SimpleTestCase

from .services import Charge, Discount, PricingError, calculate_price

D = Decimal


class PricingTests(SimpleTestCase):
    """No database access is permitted: previews must remain side-effect free."""

    def test_approved_percentage_example(self):
        rule = Discount("ten-percent", "PERCENTAGE", D("10"))
        result = calculate_price(
            [
                Charge("plan", 1, D("100.00"), tax_rate=D("5"), discount=rule),
                Charge("product", 2, D("50.00"), tax_rate=D("5"), discount=rule),
            ]
        )
        self.assertEqual(result.currency, "INR")
        self.assertEqual(
            (result.subtotal, result.discount, result.net, result.tax, result.total),
            (D("200"), D("20"), D("180"), D("9"), D("189")),
        )

    def test_fixed_discount_is_once_per_rule_and_ties_use_stable_ids(self):
        rule = Discount("one-off", "FIXED", D("1.00"))
        charges = [Charge(key, 1, D("1.00"), tax_rate=D("5"), discount=rule) for key in "ABC"]
        for ordering in permutations(charges):
            result = calculate_price(ordering)
            self.assertEqual(result.total, D("2.09"))
            self.assertEqual(result.discount, D("1.00"))
            self.assertEqual(
                {line.charge_id: line.discount for line in result.lines},
                {"A": D(".34"), "B": D(".33"), "C": D(".33")},
            )
            self.assertEqual(
                [line.charge_id for line in result.lines], [c.charge_id for c in ordering]
            )

    def test_tax_half_cent_rounds_up_per_line(self):
        result = calculate_price([Charge("a", 1, D(".10"), tax_rate=D("5"))])
        self.assertEqual(result.tax, D(".01"))
        self.assertEqual(result.total, D(".11"))

    def test_percentage_discount_rounds_half_up_per_line(self):
        rule = Discount("half", "PERCENTAGE", D("50"))
        result = calculate_price([Charge(key, 1, D(".01"), discount=rule) for key in "AB"])
        self.assertEqual(result.discount, D(".02"))
        self.assertEqual(result.total, D("0.00"))

    def test_product_scope_excludes_plan_and_other_products(self):
        rule = Discount("product-rule", "FIXED", D("5.00"), "PRODUCT", "p1")
        result = calculate_price(
            [
                Charge("plan", 1, D("10.00")),
                Charge("a", 1, D("10.00"), product_id="p1", discount=rule),
                Charge("b", 1, D("10.00"), product_id="p2"),
            ]
        )
        self.assertEqual(result.total, D("25.00"))
        self.assertEqual([line.discount for line in result.lines], [D("0"), D("5"), D("0")])
        for product_id in [None, "p2"]:
            with self.subTest(product_id=product_id), self.assertRaises(PricingError):
                calculate_price([Charge("a", 1, D("10"), product_id=product_id, discount=rule)])

    def test_fixed_discount_caps_at_eligible_gross(self):
        rule = Discount("large", "FIXED", D("100.00"))
        result = calculate_price(
            [
                Charge("a", 1, D("2.00"), tax_rate=D("10"), discount=rule),
                Charge("b", 1, D("0.00"), tax_rate=D("10"), discount=rule),
            ]
        )
        self.assertEqual(result.discount, D("2.00"))
        self.assertEqual(result.total, D("0.00"))

    def test_zero_gross_and_zero_discount_do_not_divide_by_zero(self):
        for amount in [D("0"), D("5")]:
            rule = Discount("fixed", "FIXED", amount)
            result = calculate_price([Charge("a", 1, D("0"), discount=rule)])
            self.assertEqual(result.total, D("0.00"))

    def test_variant_adjustment_applies_per_unit(self):
        result = calculate_price([Charge("a", 2, D("1200.00"), D("560.00"))])
        self.assertEqual(result.total, D("3520.00"))
        self.assertEqual(calculate_price([Charge("a", 1, D("10"), D("-10"))]).total, D("0"))
        with self.assertRaises(PricingError):
            calculate_price([Charge("a", 1, D("10"), D("-11"))])

    def test_invalid_money_is_rejected(self):
        for value in [1.25, "1.25", 1, True, D("NaN"), D("Infinity"), D("-.01"), D(".001")]:
            with self.subTest(value=value), self.assertRaises(PricingError):
                calculate_price([Charge("a", 1, value)])

    def test_invalid_quantities_are_rejected(self):
        for value in [0, -1, True, 1.0, D("1"), "1", None]:
            with self.subTest(value=value), self.assertRaises(PricingError):
                calculate_price([Charge("a", value, D("1"))])

    def test_tax_and_discount_percentage_boundaries(self):
        for value in [D("-1"), D("100.01"), D("NaN"), 5.0]:
            with self.subTest(value=value):
                with self.assertRaises(PricingError):
                    calculate_price([Charge("a", 1, D("1"), tax_rate=value)])
                with self.assertRaises(PricingError):
                    calculate_price(
                        [Charge("a", 1, D("1"), discount=Discount("r", "PERCENTAGE", value))]
                    )
        for rate in [D("0"), D("100")]:
            result = calculate_price([Charge("a", 1, D("1"), tax_rate=rate)])
            self.assertEqual(result.tax, rate / 100)

    def test_conflicting_rule_definitions_and_duplicate_lines_fail(self):
        rule = Discount("r", "FIXED", D("1"))
        a = Charge("a", 1, D("10"), discount=rule)
        with self.assertRaises(PricingError):
            calculate_price([a, a])
        with self.assertRaises(PricingError):
            calculate_price([a, replace(a, charge_id="b", discount=replace(rule, value=D("2")))])

    def test_invalid_rules_fail_instead_of_silently_being_ignored(self):
        for rule in [
            [],
            Discount("", "FIXED", D("1")),
            Discount("r", "OTHER", D("1")),
            Discount("r", "FIXED", D("-1")),
            Discount("r", "FIXED", D(".001")),
            Discount("r", "FIXED", D("1"), "OTHER"),
            Discount("r", "FIXED", D("1"), "PRODUCT"),
            Discount("r", "FIXED", D("1"), "SUBSCRIPTION", "p"),
        ]:
            with self.subTest(rule=rule), self.assertRaises(PricingError):
                calculate_price([Charge("a", 1, D("10"), discount=rule)])

    def test_invalid_shape_and_currency(self):
        for charges in [None, [None], [Charge(" ", 1, D("1"))]]:
            with self.subTest(charges=charges), self.assertRaises(PricingError):
                calculate_price(charges)
        with self.assertRaises(PricingError):
            calculate_price([], currency="USD")

    def test_empty_preview_and_exact_decimal_output(self):
        result = calculate_price([])
        self.assertEqual(result.lines, ())
        self.assertEqual(str(result.total), "0.00")

    def test_caller_decimal_context_cannot_change_totals(self):
        charges = [Charge("a", 100, D("9999999999.99"), tax_rate=D("12.34567"))]
        expected = calculate_price(charges)
        with localcontext() as ctx:
            ctx.prec = 3
            self.assertEqual(calculate_price(charges), expected)

    def test_allocation_reconciles_and_never_exceeds_a_charge(self):
        # Exercise uneven shares, zero-value lines, ties and capped budgets.
        for a in range(5):
            for b in range(5):
                for budget in range(12):
                    rule = Discount("r", "FIXED", D(budget) / 100)
                    result = calculate_price(
                        [
                            Charge("a", 1, D(a) / 100, discount=rule),
                            Charge("b", 1, D(b) / 100, discount=rule),
                            Charge("c", 1, D(".01"), discount=rule),
                        ]
                    )
                    self.assertEqual(result.discount, min(D(budget), D(a + b + 1)) / 100)
                    self.assertEqual(sum(line.total for line in result.lines), result.total)
                    for line in result.lines:
                        self.assertGreaterEqual(line.net, 0)
                        self.assertLessEqual(line.discount, line.gross)

    def test_independent_rules_and_fractional_rates(self):
        fixed = Discount("fixed", "FIXED", D(".50"))
        percent = Discount("percent", "PERCENTAGE", D("12.3456"))
        result = calculate_price(
            [
                Charge("a", 1, D("1"), discount=fixed),
                Charge("b", 1, D("1"), discount=percent),
            ]
        )
        self.assertEqual(result.discount, D(".62"))
        self.assertEqual(result.total, D("1.38"))
