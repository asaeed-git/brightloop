import threading
import uuid
from decimal import Decimal

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from billing.models import Invoice
from payments.models import Payment
from payments.services import (
    InvalidPaymentError,
    OverpaymentError,
    PaymentConflictError,
    record_payment,
)


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
        )
        self.other_customer = User.objects.create_user(
            email="other@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
        )
        self.staff_user = User.objects.create_user(
            email="staff@example.com",
            password="StrongPassword123!",
            role=User.Role.STAFF,
        )

        today = timezone.localdate()
        self.invoice = Invoice.objects.create(
            number="INV-202610-0099",
            customer=self.customer,
            status=Invoice.Status.CONFIRMED,
            period_start=today,
            period_end=today + timezone.timedelta(days=30),
            issue_date=today,
            due_date=today + timezone.timedelta(days=15),
            subtotal=Decimal("1000.00"),
            discount_total=Decimal("100.00"),
            net_total=Decimal("900.00"),
            tax_total=Decimal("162.00"),
            total=Decimal("1062.00"),
            amount_paid=Decimal("0.00"),
        )

    def test_partial_payment_updates_amount_paid_and_keeps_confirmed(self):
        payment = record_payment(
            invoice=self.invoice,
            amount=Decimal("500.00"),
            method=Payment.Method.UPI,
            idempotency_key="key-part-1",
            transaction_ref="UPI123456",
        )

        self.assertEqual(payment.amount, Decimal("500.00"))
        self.assertEqual(payment.method, Payment.Method.UPI)
        self.assertEqual(payment.customer, self.customer)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("500.00"))
        self.assertEqual(self.invoice.amount_due, Decimal("562.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.CONFIRMED)
        self.assertIsNone(self.invoice.paid_at)

    def test_full_payment_transitions_to_paid_and_sets_paid_at(self):
        payment = record_payment(
            invoice=self.invoice,
            amount=Decimal("1062.00"),
            method=Payment.Method.BANK_TRANSFER,
            idempotency_key="key-full-1",
            transaction_ref="NEFT999888",
        )

        self.assertEqual(payment.amount, Decimal("1062.00"))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("1062.00"))
        self.assertEqual(self.invoice.amount_due, Decimal("0.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertIsNotNone(self.invoice.paid_at)

    def test_multiple_partial_payments_accumulate_to_full_settlement(self):
        record_payment(
            invoice=self.invoice,
            amount=Decimal("600.00"),
            method=Payment.Method.CARD,
            idempotency_key="key-accum-1",
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(self.invoice.amount_due, Decimal("462.00"))

        record_payment(
            invoice=self.invoice,
            amount=Decimal("462.00"),
            method=Payment.Method.UPI,
            idempotency_key="key-accum-2",
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertEqual(self.invoice.amount_paid, Decimal("1062.00"))
        self.assertEqual(self.invoice.amount_due, Decimal("0.00"))
        self.assertIsNotNone(self.invoice.paid_at)

    def test_overpayment_rejected_and_state_unmutated(self):
        with self.assertRaises(OverpaymentError):
            record_payment(
                invoice=self.invoice,
                amount=Decimal("1100.00"),
                method=Payment.Method.CARD,
                idempotency_key="key-over-1",
            )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("0.00"))
        self.assertEqual(self.invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(Payment.objects.filter(invoice=self.invoice).count(), 0)

    def test_payment_on_unpayable_invoice_raises_invalid_payment_error(self):
        self.invoice.status = Invoice.Status.DRAFT
        self.invoice.save()

        with self.assertRaises(InvalidPaymentError):
            record_payment(
                invoice=self.invoice,
                amount=Decimal("100.00"),
                method=Payment.Method.CARD,
                idempotency_key="key-draft-pay",
            )

        self.invoice.status = Invoice.Status.PAID
        self.invoice.save()

        with self.assertRaises(InvalidPaymentError):
            record_payment(
                invoice=self.invoice,
                amount=Decimal("100.00"),
                method=Payment.Method.CARD,
                idempotency_key="key-paid-pay",
            )

    def test_idempotent_replay_returns_existing_payment_without_double_debit(self):
        p1 = record_payment(
            invoice=self.invoice,
            amount=Decimal("300.00"),
            method=Payment.Method.CARD,
            idempotency_key="idemp-key-replay",
        )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("300.00"))

        # Replay exact same request
        p2 = record_payment(
            invoice=self.invoice,
            amount=Decimal("300.00"),
            method=Payment.Method.CARD,
            idempotency_key="idemp-key-replay",
        )

        self.assertEqual(p1.pk, p2.pk)
        self.assertEqual(Payment.objects.filter(idempotency_key="idemp-key-replay").count(), 1)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.amount_paid, Decimal("300.00"))

    def test_idempotent_replay_with_conflicting_payload_raises_error(self):
        record_payment(
            invoice=self.invoice,
            amount=Decimal("300.00"),
            method=Payment.Method.CARD,
            idempotency_key="idemp-key-conflict",
        )

        with self.assertRaises(PaymentConflictError):
            record_payment(
                invoice=self.invoice,
                amount=Decimal("500.00"),  # Different amount!
                method=Payment.Method.CARD,
                idempotency_key="idemp-key-conflict",
            )

        with self.assertRaises(PaymentConflictError):
            record_payment(
                invoice=self.invoice,
                amount=Decimal("300.00"),
                method=Payment.Method.UPI,  # Different method!
                idempotency_key="idemp-key-conflict",
            )

    def test_payment_amount_positive_db_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Payment.objects.create(
                    invoice=self.invoice,
                    customer=self.customer,
                    idempotency_key="zero-amount-key",
                    method=Payment.Method.CARD,
                    amount=Decimal("0.00"),
                )


class PaymentConcurrencyTests(TransactionTestCase):
    """Verifies that select_for_update prevents race conditions on balance settlement."""

    def test_concurrent_payments_cannot_overpay_invoice(self):
        customer = User.objects.create_user(
            email="conc-customer@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
        )
        today = timezone.localdate()
        invoice = Invoice.objects.create(
            number="INV-202610-CONC",
            customer=customer,
            status=Invoice.Status.CONFIRMED,
            period_start=today,
            period_end=today + timezone.timedelta(days=30),
            issue_date=today,
            due_date=today + timezone.timedelta(days=15),
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
            amount_paid=Decimal("0.00"),
        )

        # Two threads try to pay 60.00 concurrently on an invoice of total 100.00.
        # Combined = 120.00 > 100.00. Exactly one must succeed, and the other must raise OverpaymentError.
        results = []
        errors = []

        def pay_worker(key):
            connection.close()  # Get a fresh connection in the thread
            try:
                p = record_payment(
                    invoice=invoice,
                    amount=Decimal("60.00"),
                    method=Payment.Method.CARD,
                    idempotency_key=key,
                )
                results.append(p)
            except OverpaymentError as e:
                errors.append(e)
            finally:
                connection.close()

        t1 = threading.Thread(target=pay_worker, args=("conc-key-1",))
        t2 = threading.Thread(target=pay_worker, args=("conc-key-2",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)

        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("60.00"))
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)


class PaymentViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPassword123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="StrongPassword123!",
            role=User.Role.STAFF,
        )
        self.customer1 = User.objects.create_user(
            email="customer1@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
        )
        self.customer2 = User.objects.create_user(
            email="customer2@example.com",
            password="StrongPassword123!",
            role=User.Role.CUSTOMER,
        )

        today = timezone.localdate()
        self.invoice1 = Invoice.objects.create(
            number="INV-202610-0101",
            customer=self.customer1,
            status=Invoice.Status.CONFIRMED,
            period_start=today,
            period_end=today + timezone.timedelta(days=30),
            issue_date=today,
            due_date=today + timezone.timedelta(days=15),
            subtotal=Decimal("500.00"),
            total=Decimal("500.00"),
            amount_paid=Decimal("0.00"),
        )
        self.invoice2 = Invoice.objects.create(
            number="INV-202610-0102",
            customer=self.customer2,
            status=Invoice.Status.CONFIRMED,
            period_start=today,
            period_end=today + timezone.timedelta(days=30),
            issue_date=today,
            due_date=today + timezone.timedelta(days=15),
            subtotal=Decimal("800.00"),
            total=Decimal("800.00"),
            amount_paid=Decimal("0.00"),
        )

    def test_staff_payment_list_access(self):
        self.client.login(email="staff@example.com", password="StrongPassword123!")
        response = self.client.get(reverse("payments:payment_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payments/payment_list.html")

    def test_customer_cannot_access_staff_payment_list(self):
        self.client.login(email="customer1@example.com", password="StrongPassword123!")
        response = self.client.get(reverse("payments:payment_list"))
        self.assertEqual(response.status_code, 403)

    def test_staff_payment_create_post(self):
        self.client.login(email="staff@example.com", password="StrongPassword123!")
        response = self.client.post(
            reverse("payments:payment_create", kwargs={"invoice_pk": self.invoice1.pk}),
            {
                "method": "BANK_TRANSFER",
                "amount": "250.00",
                "transaction_ref": "UTR-112233",
                "notes": "Bank check received",
                "idempotency_key": str(uuid.uuid4()),
            },
        )
        self.assertRedirects(
            response, reverse("billing:invoice_detail", kwargs={"pk": self.invoice1.pk})
        )

        self.invoice1.refresh_from_db()
        self.assertEqual(self.invoice1.amount_paid, Decimal("250.00"))
        self.assertEqual(self.invoice1.payments.count(), 1)

    def test_customer_self_service_simulate_payment(self):
        self.client.login(email="customer1@example.com", password="StrongPassword123!")
        response = self.client.post(
            reverse("payments:customer_payment_create", kwargs={"invoice_pk": self.invoice1.pk}),
            {
                "amount": "500.00",
                "method": "SIMULATED",
            },
        )
        self.assertRedirects(
            response,
            reverse("billing:customer_invoice_detail", kwargs={"pk": self.invoice1.pk}),
        )

        self.invoice1.refresh_from_db()
        self.assertEqual(self.invoice1.status, Invoice.Status.PAID)
        self.assertEqual(self.invoice1.amount_paid, Decimal("500.00"))
        self.assertEqual(self.invoice1.payments.count(), 1)

    def test_customer_cannot_pay_another_customers_invoice(self):
        # Customer 1 attempts to pay Customer 2's invoice
        self.client.login(email="customer1@example.com", password="StrongPassword123!")
        response = self.client.post(
            reverse("payments:customer_payment_create", kwargs={"invoice_pk": self.invoice2.pk}),
            {
                "amount": "800.00",
                "method": "SIMULATED",
            },
        )
        # scope_to_customer filters invoice2 out for customer1, so get_object_or_404 raises 404
        self.assertEqual(response.status_code, 404)
        self.invoice2.refresh_from_db()
        self.assertEqual(self.invoice2.amount_paid, Decimal("0.00"))

    def test_overdue_filter_on_staff_invoice_list(self):
        past_date = timezone.localdate() - timezone.timedelta(days=5)
        self.invoice1.due_date = past_date
        self.invoice1.save()

        self.client.login(email="staff@example.com", password="StrongPassword123!")
        response = self.client.get(reverse("billing:invoice_list"), {"status": "OVERDUE"})
        self.assertEqual(response.status_code, 200)
        invoices = list(response.context["invoices"])
        self.assertIn(self.invoice1, invoices)
        self.assertNotIn(self.invoice2, invoices)

    def test_customer_invoice_list_shows_account_balances(self):
        self.client.login(email="customer1@example.com", password="StrongPassword123!")
        response = self.client.get(reverse("billing:customer_invoice_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_invoiced"], Decimal("500.00"))
        self.assertEqual(response.context["total_paid"], Decimal("0.00"))
        self.assertEqual(response.context["total_outstanding"], Decimal("500.00"))
