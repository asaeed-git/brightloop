from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from .admin import AdminAccountCreationForm
from .models import User
from .permissions import require_roles, scope_to_customer
from .validators import BrightloopPasswordValidator


class PasswordTests(SimpleTestCase):
    def test_requires_more_than_eight_and_each_character_class(self):
        validator = BrightloopPasswordValidator()
        for password in ["Abcdefg!", "lowercase!", "UPPERCASE!", "NoSpecial123", "Abcdefgh "]:
            with self.subTest(password=password), self.assertRaises(ValidationError):
                validator.validate(password)

    def test_digit_is_not_required(self):
        BrightloopPasswordValidator().validate("LongPhrase!")


class IdentityTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user("First@Example.com", "LongPhrase!")
        self.other = User.objects.create_user("second@example.com", "LongPhrase!")

    def test_normalizes_email_and_hashes_password(self):
        self.assertEqual(self.customer.email, "first@example.com")
        self.assertNotEqual(self.customer.password, "LongPhrase!")
        self.assertTrue(self.customer.check_password("LongPhrase!"))
        self.assertEqual(
            authenticate(email=self.customer.email, password="LongPhrase!"), self.customer
        )

    def test_database_rejects_case_insensitive_duplicate_even_bypassing_save(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(email="FIRST@example.com")])

    def test_authentication_accepts_email_case_variations(self):
        self.assertEqual(
            authenticate(email=" FIRST@Example.com ", password="LongPhrase!"), self.customer
        )

    def test_database_rejects_privilege_flags_for_customer(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=self.customer.pk).update(is_staff=True)

    def test_database_rejects_unknown_roles(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=self.customer.pk).update(role="OWNER")

    def test_superuser_must_be_admin(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser("bad@example.com", role=User.Role.CUSTOMER)

    def test_role_checks_fail_closed(self):
        for user in [AnonymousUser(), self.customer]:
            with self.subTest(user=str(user)), self.assertRaises(PermissionDenied):
                require_roles(user, User.Role.ADMIN)
        self.customer.is_active = False
        with self.assertRaises(PermissionDenied):
            require_roles(self.customer, User.Role.CUSTOMER)

    def test_customer_scope_excludes_other_accounts(self):
        scoped = scope_to_customer(User.objects.all(), self.customer, customer_field="pk")
        self.assertEqual(list(scoped), [self.customer])

    def test_staff_cannot_open_admin_or_create_users(self):
        staff = User.objects.create_user("staff@example.com", "LongPhrase!", role=User.Role.STAFF)
        self.client.force_login(staff)
        response = self.client.post("/admin/accounts/user/add/", {"email": "attacker@example.com"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
        self.assertFalse(User.objects.filter(email="attacker@example.com").exists())

    def test_admin_can_create_staff_through_form(self):
        form = AdminAccountCreationForm(
            data={
                "email": "operator@example.com",
                "role": User.Role.STAFF,
                "usable_password": "true",
                "password1": "LongPhrase!",
                "password2": "LongPhrase!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        staff = form.save()
        self.assertEqual(staff.role, User.Role.STAFF)
        self.assertFalse(staff.is_staff)

    def test_admin_account_pages_render(self):
        admin = User.objects.create_superuser("admin@example.com", "LongPhrase!")
        self.client.force_login(admin)
        for url in ["/admin/", "/admin/accounts/user/", "/admin/accounts/user/add/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
