import datetime
import random
import uuid
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from billing.models import Invoice, InvoiceLine
from catalog.models import Product, ProductVariant
from payments.models import Payment
from plans.models import Plan
from subscriptions.models import Subscription, SubscriptionLine


class Command(BaseCommand):
    help = "Seed a repeatable scale dataset with hundreds or thousands of subscriptions, invoices, and payments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--subscriptions",
            type=int,
            default=500,
            help="Number of subscriptions to seed (default: 500).",
        )
        parser.add_argument(
            "--customers",
            type=int,
            default=100,
            help="Number of customers to distribute subscriptions across (default: 100).",
        )
        parser.add_argument(
            "--prefix",
            type=str,
            default="scale",
            help="Prefix for generated emails and references (default: 'scale').",
        )

    def handle(self, *args, **options):
        count = options["subscriptions"]
        customer_count = options["customers"]
        prefix = options["prefix"]

        self.stdout.write(
            f"Seeding scale dataset: {count} subscriptions across {customer_count} customers..."
        )

        today = timezone.localdate()

        with transaction.atomic():
            # 1. Ensure Plans and Products exist
            plan, _ = Plan.objects.get_or_create(
                code=f"{prefix}-pro",
                defaults={
                    "name": "Scale Pro Plan",
                    "interval": Plan.Interval.MONTHLY,
                    "price": Decimal("999.00"),
                    "is_active": True,
                },
            )
            product, _ = Product.objects.get_or_create(
                name="Scale Add-on Service",
                defaults={
                    "sales_price": Decimal("250.00"),
                    "cost_price": Decimal("100.00"),
                    "is_active": True,
                },
            )
            variant, _ = ProductVariant.objects.get_or_create(
                product=product,
                name="Default",
                defaults={
                    "price_extra": Decimal("0.00"),
                    "is_active": True,
                },
            )

            # 2. Create Customers
            existing_customers = list(
                User.objects.filter(email__startswith=f"{prefix}_customer_")[:customer_count]
            )
            customers_to_create = []
            for i in range(len(existing_customers), customer_count):
                u = User(
                    email=f"{prefix}_customer_{i:04d}@example.com",
                    role=User.Role.CUSTOMER,
                    is_active=True,
                )
                u.set_password("ScalePassword123!")
                customers_to_create.append(u)

            if customers_to_create:
                User.objects.bulk_create(customers_to_create, batch_size=500)
                all_customers = list(User.objects.filter(email__startswith=f"{prefix}_customer_"))
            else:
                all_customers = existing_customers

            self.stdout.write(f"  Available customers: {len(all_customers)}")

            # 3. Create Subscriptions
            subs_to_create = []
            for i in range(count):
                cust = random.choice(all_customers)
                # Distribute statuses: 70% ACTIVE, 10% ACTIVE paused, 10% QUOTATION, 10% CLOSED
                r = random.random()
                if r < 0.70:
                    status = Subscription.Status.ACTIVE
                    is_paused = False
                elif r < 0.80:
                    status = Subscription.Status.ACTIVE
                    is_paused = True
                elif r < 0.90:
                    status = Subscription.Status.QUOTATION
                    is_paused = False
                else:
                    status = Subscription.Status.CLOSED
                    is_paused = False

                period_start = today - datetime.timedelta(days=random.randint(1, 90))
                period_end = period_start + datetime.timedelta(days=30)
                next_billing = period_end if status == Subscription.Status.ACTIVE else None

                sub = Subscription(
                    number=f"SUB-{prefix.upper()}-{i:05d}",
                    customer=cust,
                    plan=plan,
                    status=status,
                    is_paused=is_paused,
                    start_date=period_start,
                    current_period_start=period_start,
                    current_period_end=period_end,
                    next_billing_date=next_billing,
                    base_price=plan.price,
                    payment_terms_days=15,
                )
                subs_to_create.append(sub)

            created_subs = Subscription.objects.bulk_create(subs_to_create, batch_size=500)
            self.stdout.write(f"  Created {len(created_subs)} subscriptions.")

            # 4. Create Subscription Lines
            lines_to_create = []
            for sub in created_subs:
                lines_to_create.append(
                    SubscriptionLine(
                        subscription=sub,
                        product=product,
                        variant=variant,
                        quantity=random.randint(1, 5),
                        unit_price=Decimal("250.00"),
                    )
                )
            SubscriptionLine.objects.bulk_create(lines_to_create, batch_size=500)

            # 5. Create Invoices and Payments for a subset of subscriptions
            invoices_to_create = []
            payments_to_create = []
            invoice_lines_to_create = []

            for i, sub in enumerate(created_subs):
                if sub.status in [Subscription.Status.ACTIVE, Subscription.Status.CLOSED]:
                    issue_date = sub.current_period_start
                    due_date = issue_date + datetime.timedelta(days=15)
                    subtotal = Decimal("1249.00")
                    tax_total = Decimal("224.82")
                    total = Decimal("1473.82")

                    # 60% fully paid, 25% partially paid, 15% unpaid (overdue if due_date < today)
                    p_roll = random.random()
                    if p_roll < 0.60:
                        inv_status = Invoice.Status.PAID
                        amount_paid = total
                        paid_at = timezone.make_aware(
                            datetime.datetime.combine(
                                issue_date + datetime.timedelta(days=2),
                                datetime.time(10, 0),
                            )
                        )
                    elif p_roll < 0.85:
                        inv_status = Invoice.Status.CONFIRMED
                        amount_paid = Decimal("700.00")
                        paid_at = timezone.make_aware(
                            datetime.datetime.combine(
                                issue_date + datetime.timedelta(days=3),
                                datetime.time(11, 0),
                            )
                        )
                    else:
                        inv_status = Invoice.Status.CONFIRMED
                        amount_paid = Decimal("0.00")
                        paid_at = None

                    inv = Invoice(
                        number=f"INV-{prefix.upper()}-{i:05d}",
                        customer=sub.customer,
                        subscription=sub,
                        status=inv_status,
                        period_start=sub.current_period_start,
                        period_end=sub.current_period_end,
                        issue_date=issue_date,
                        due_date=due_date,
                        subtotal=subtotal,
                        discount_total=Decimal("0.00"),
                        net_total=subtotal,
                        tax_total=tax_total,
                        total=total,
                        amount_paid=amount_paid,
                        paid_at=paid_at if inv_status == Invoice.Status.PAID else None,
                    )
                    invoices_to_create.append((inv, amount_paid, paid_at))

            # Bulk create invoices
            raw_invs = [item[0] for item in invoices_to_create]
            created_invs = Invoice.objects.bulk_create(raw_invs, batch_size=500)
            self.stdout.write(f"  Created {len(created_invs)} invoices.")

            # Create lines and payments for the created invoices
            methods = [Payment.Method.UPI, Payment.Method.CARD, Payment.Method.BANK_TRANSFER]
            for idx, inv in enumerate(created_invs):
                _, amount_paid, paid_at = invoices_to_create[idx]

                invoice_lines_to_create.append(
                    InvoiceLine(
                        invoice=inv,
                        product=product,
                        description="Scale Service Snapshot",
                        quantity=1,
                        unit_price=inv.subtotal,
                        gross=inv.subtotal,
                        discount=Decimal("0.00"),
                        net=inv.subtotal,
                        tax=inv.tax_total,
                        total=inv.total,
                    )
                )

                if amount_paid > Decimal("0.00") and paid_at is not None:
                    payments_to_create.append(
                        Payment(
                            invoice=inv,
                            customer=inv.customer,
                            idempotency_key=str(uuid.uuid4()),
                            method=random.choice(methods),
                            amount=amount_paid,
                            paid_at=paid_at,
                            transaction_ref=f"SCALE-{idx:05d}",
                            notes="Scale test payment",
                        )
                    )

            InvoiceLine.objects.bulk_create(invoice_lines_to_create, batch_size=500)
            Payment.objects.bulk_create(payments_to_create, batch_size=500)
            self.stdout.write(f"  Created {len(payments_to_create)} payments.")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded scale dataset with {count} subscriptions, "
                f"{len(created_invs)} invoices, and {len(payments_to_create)} payments!"
            )
        )
