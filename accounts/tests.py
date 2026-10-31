from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .admin import AdminAccountCreationForm
from .forms import SignupForm
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


class SignupFormTests(TestCase):
    """Unit tests for SignupForm; view-level flow tested in AuthFlowTests."""

    def test_valid_data_creates_customer_with_normalized_email(self):
        form = SignupForm(
            data={
                "email": "New@Example.com",
                "password1": "LongPhrase!",
                "password2": "LongPhrase!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(user.check_password("LongPhrase!"))

    def test_role_is_always_customer_even_if_extra_data_submitted(self):
        """Role field is not in Meta.fields; form cannot be manipulated to set ADMIN."""
        form = SignupForm(
            data={
                "email": "hacker@example.com",
                "password1": "LongPhrase!",
                "password2": "LongPhrase!",
                "role": "ADMIN",  # attempt to inject a privileged role
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.role, User.Role.CUSTOMER)

    def test_duplicate_email_rejected_case_insensitively(self):
        User.objects.create_user("existing@example.com", "LongPhrase!")
        for email in ["existing@example.com", "EXISTING@example.com", "Existing@Example.COM"]:
            with self.subTest(email=email):
                form = SignupForm(
                    data={"email": email, "password1": "LongPhrase!", "password2": "LongPhrase!"}
                )
                self.assertFalse(form.is_valid())
                self.assertIn("email", form.errors)

    def test_password_mismatch_rejected(self):
        form = SignupForm(
            data={
                "email": "user@example.com",
                "password1": "LongPhrase!",
                "password2": "DifferentOne#",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_weak_password_rejected(self):
        for password in ["short", "alllowercase!", "NOLOWER!"]:
            with self.subTest(password=password):
                form = SignupForm(
                    data={
                        "email": "user@example.com",
                        "password1": password,
                        "password2": password,
                    }
                )
                self.assertFalse(form.is_valid())


class AuthFlowTests(TestCase):
    """Integration tests for public signup, login, logout, and password reset views."""

    SIGNUP_URL = "/accounts/signup/"
    LOGIN_URL = "/accounts/login/"
    LOGOUT_URL = "/accounts/logout/"
    RESET_URL = "/accounts/password-reset/"

    def setUp(self):
        self.existing = User.objects.create_user("existing@example.com", "LongPhrase!")

    # ── Signup ────────────────────────────────────────────────────────────────

    def test_signup_get_renders_form(self):
        response = self.client.get(self.SIGNUP_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")

    def test_signup_creates_customer_and_logs_in(self):
        response = self.client.post(
            self.SIGNUP_URL,
            {"email": "new@example.com", "password1": "LongPhrase!", "password2": "LongPhrase!"},
        )
        self.assertRedirects(response, "/")
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        # Session should be active (user logged in after signup)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_signup_normalizes_email(self):
        self.client.post(
            self.SIGNUP_URL,
            {
                "email": "  Mixed@Example.COM  ",
                "password1": "LongPhrase!",
                "password2": "LongPhrase!",
            },
        )
        self.assertTrue(User.objects.filter(email="mixed@example.com").exists())

    def test_signup_rejects_duplicate_email(self):
        response = self.client.post(
            self.SIGNUP_URL,
            {
                "email": "existing@example.com",
                "password1": "LongPhrase!",
                "password2": "LongPhrase!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")

    def test_signup_rejects_weak_password(self):
        response = self.client.post(
            self.SIGNUP_URL,
            {"email": "new@example.com", "password1": "weak", "password2": "weak"},
        )
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_is_redirected_from_signup(self):
        self.client.force_login(self.existing)
        response = self.client.get(self.SIGNUP_URL)
        self.assertRedirects(response, "/")

    # ── Login ─────────────────────────────────────────────────────────────────

    def test_login_get_renders_form(self):
        response = self.client.get(self.LOGIN_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to Brightloop")

    def test_login_with_correct_credentials_redirects_to_home(self):
        response = self.client.post(
            self.LOGIN_URL,
            {"username": "existing@example.com", "password": "LongPhrase!"},
        )
        self.assertRedirects(response, "/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_normalizes_email_case(self):
        response = self.client.post(
            self.LOGIN_URL,
            {"username": "EXISTING@EXAMPLE.COM", "password": "LongPhrase!"},
        )
        self.assertRedirects(response, "/")

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            self.LOGIN_URL,
            {"username": "existing@example.com", "password": "WrongPassword!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_inactive_user_is_denied(self):
        self.existing.is_active = False
        self.existing.save()
        response = self.client.post(
            self.LOGIN_URL,
            {"username": "existing@example.com", "password": "LongPhrase!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_throttle_uses_remote_addr_ignoring_spoofed_forwarded_for(self):
        from django.core.cache import cache
        from django.test import RequestFactory

        from accounts.throttle import check_throttle

        cache.clear()
        factory = RequestFactory()
        for i in range(10):
            req = factory.post(
                "/accounts/login/", REMOTE_ADDR="192.0.2.1", HTTP_X_FORWARDED_FOR=f"10.0.0.{i}"
            )
            self.assertTrue(check_throttle(req, "test_action", limit=10, window=60))

        blocked_req = factory.post(
            "/accounts/login/", REMOTE_ADDR="192.0.2.1", HTTP_X_FORWARDED_FOR="10.0.0.99"
        )
        self.assertFalse(check_throttle(blocked_req, "test_action", limit=10, window=60))

    # ── Logout ────────────────────────────────────────────────────────────────

    def test_logout_post_clears_session_and_redirects(self):
        self.client.force_login(self.existing)
        self.assertIn("_auth_user_id", self.client.session)
        response = self.client.post(self.LOGOUT_URL)
        self.assertRedirects(response, "/")
        self.assertNotIn("_auth_user_id", self.client.session)

    # ── Password reset ────────────────────────────────────────────────────────

    def test_password_reset_get_renders_form(self):
        response = self.client.get(self.RESET_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset your password")

    def test_password_reset_sends_email_for_existing_account(self):
        response = self.client.post(self.RESET_URL, {"email": "existing@example.com"})
        self.assertRedirects(response, "/accounts/password-reset/sent/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("existing@example.com", mail.outbox[0].to)

    def test_password_reset_does_not_reveal_nonexistent_account(self):
        """Same redirect happens whether or not the address has an account."""
        response = self.client.post(self.RESET_URL, {"email": "nobody@example.com"})
        self.assertRedirects(response, "/accounts/password-reset/sent/")
        self.assertEqual(len(mail.outbox), 0)  # no email sent, but same outcome to user

    def test_password_reset_link_sets_new_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.existing.pk))
        token = default_token_generator.make_token(self.existing)
        confirm_url = f"/accounts/reset/{uid}/{token}/"

        # First GET validates the token, stores it in session, and redirects to set-password URL
        response = self.client.get(confirm_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a new password")

        # POST the new password to complete the reset
        response = self.client.post(
            f"/accounts/reset/{uid}/set-password/",
            {"new_password1": "BrandNewPhrase#", "new_password2": "BrandNewPhrase#"},
        )
        self.assertRedirects(response, "/accounts/reset/complete/")
        self.existing.refresh_from_db()
        self.assertTrue(self.existing.check_password("BrandNewPhrase#"))

    def test_password_reset_invalid_link_shows_error(self):
        uid = urlsafe_base64_encode(force_bytes(self.existing.pk))
        response = self.client.get(f"/accounts/reset/{uid}/invalid-token/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "invalid or has already been used")

    def test_password_reset_normalizes_email(self):
        """Upper-case email in reset form still matches the account."""
        response = self.client.post(self.RESET_URL, {"email": "EXISTING@EXAMPLE.COM"})
        self.assertRedirects(response, "/accounts/password-reset/sent/")
        self.assertEqual(len(mail.outbox), 1)


class ProfileTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            "customer@example.com", "LongPhrase!", role=User.Role.CUSTOMER
        )

    def test_profile_requires_login(self):
        response = self.client.get("/accounts/profile/")
        self.assertRedirects(response, "/accounts/login/?next=/accounts/profile/")

    def test_profile_get_renders_customer_info(self):
        self.client.force_login(self.customer)
        response = self.client.get("/accounts/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "customer@example.com")
        self.assertContains(response, "Customer")

    def test_profile_post_updates_name(self):
        self.client.force_login(self.customer)
        response = self.client.post(
            "/accounts/profile/",
            {"first_name": "Jane", "last_name": "Doe"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, "Jane")
        self.assertEqual(self.customer.last_name, "Doe")
