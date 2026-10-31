import time

from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from accounts.models import User
from billing.views import invoice_list
from catalog.views import product_list
from core.views import home
from plans.views import plan_list
from reporting.views import dashboard
from subscriptions.views import subscription_list


class Command(BaseCommand):
    help = "Benchmark key application pages with scale data and verify the <2s requirement."

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("Brightloop Performance & Scale Benchmark")
        self.stdout.write("Target: Page response timings strictly under 2.000s")
        self.stdout.write("=" * 60)

        factory = RequestFactory()

        # Ensure admin user
        admin = User.objects.filter(role=User.Role.ADMIN).first()
        if not admin:
            admin = User.objects.create_superuser(
                email="benchmark_admin@example.com",
                password="StrongPassword123!",
                role=User.Role.ADMIN,
            )

        views_to_test = [
            ("Home Dashboard", home, "/"),
            ("Executive Reports", dashboard, "/reporting/"),
            ("Subscriptions Directory", subscription_list, "/subscriptions/"),
            ("Invoices Directory", invoice_list, "/billing/invoices/"),
            ("Product Catalog", product_list, "/catalog/products/"),
            ("Subscription Plans", plan_list, "/plans/"),
        ]

        all_passed = True

        for name, view_func, path in views_to_test:
            request = factory.get(path)
            request.user = admin

            reset_queries()
            start_time = time.perf_counter()

            with CaptureQueriesContext(connection) as ctx:
                response = view_func(request)

            elapsed = time.perf_counter() - start_time
            num_queries = len(ctx.captured_queries)

            status_mark = "PASS" if elapsed < 2.0 and response.status_code == 200 else "FAIL"
            if status_mark == "FAIL":
                all_passed = False

            style = self.style.SUCCESS if status_mark == "PASS" else self.style.ERROR
            self.stdout.write(
                f"{name:<25} | {elapsed * 1000:6.1f} ms | {num_queries:3d} queries | "
                + style(f"[{status_mark}]")
            )

        self.stdout.write("=" * 60)
        if all_passed:
            self.stdout.write(
                self.style.SUCCESS(
                    "All measured pages satisfy the sub-2-second performance target!"
                )
            )
        else:
            self.stdout.write(self.style.ERROR("Performance targets not met on one or more views."))
