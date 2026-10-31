from django import forms
from django.contrib.auth.models import AnonymousUser
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve

from accounts.models import User


class SharedUITests(SimpleTestCase):
    def render_home(self, user, path="/"):
        request = RequestFactory().get(path)
        request.user = user
        request.resolver_match = resolve(path)
        return render_to_string("core/home.html", request=request)

    def test_anonymous_shows_sign_in_and_sign_up_links_and_no_administration_menu(self):
        """Anonymous visitors see the public auth links; admin nav is absent."""
        html = self.render_home(AnonymousUser())
        self.assertIn('href="/accounts/login/"', html)
        self.assertIn('href="/accounts/signup/"', html)
        self.assertNotIn('href="/admin/"', html)
        self.assertIn('href="#main-content"', html)
        self.assertIsNotNone(finders.find("brightloop/app.css"))

    def test_customer_navigation_requires_an_active_internal_user(self):
        for role in User.Role.values:
            for active in [True, False]:
                with self.subTest(role=role, active=active):
                    html = self.render_home(User(role=role, is_active=active))
                    self.assertEqual(
                        'href="/catalog/customers/"' in html,
                        active and role in [User.Role.ADMIN, User.Role.STAFF],
                    )

    def test_subscriptions_navigation_requires_an_active_user(self):
        for role in User.Role.values:
            for active in [True, False]:
                with self.subTest(role=role, active=active):
                    html = self.render_home(User(role=role, is_active=active))
                    self.assertEqual('href="/subscriptions/"' in html, active)

    def test_billing_navigation_requires_an_active_internal_user(self):
        for role in User.Role.values:
            for active in [True, False]:
                with self.subTest(role=role, active=active):
                    html = self.render_home(User(role=role, is_active=active))
                    expected_internal = active and role in [User.Role.ADMIN, User.Role.STAFF]
                    expected_customer = active and role == User.Role.CUSTOMER
                    self.assertEqual('href="/billing/invoices/"' in html, expected_internal)
                    self.assertEqual('href="/payments/"' in html, expected_internal)
                    self.assertEqual('href="/billing/runs/"' in html, expected_internal)
                    self.assertEqual('href="/reporting/"' in html, expected_internal)
                    self.assertEqual('href="/billing/taxes/"' in html, expected_internal)
                    self.assertEqual('href="/billing/discounts/"' in html, expected_internal)
                    self.assertEqual('href="/billing/my-invoices/"' in html, expected_customer)

    def test_variant_editor_keeps_products_navigation_active(self):
        from html.parser import HTMLParser

        class CurrentLinks(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and attrs.get("aria-current") == "page":
                    self.links.append(attrs["href"])

        parser = CurrentLinks()
        parser.feed(
            self.render_home(
                User(role=User.Role.STAFF),
                "/catalog/variants/00000000-0000-0000-0000-000000000001/edit/",
            )
        )
        self.assertEqual(parser.links, ["/catalog/products/"])

    def test_customer_home_links_to_implemented_catalog(self):
        html = self.render_home(User(role=User.Role.CUSTOMER))
        self.assertIn("Browse products", html)
        self.assertNotIn("Administrator sign in", html)

    def test_only_active_admin_with_admin_access_sees_administration(self):
        for role, active, staff, expected in [
            (User.Role.ADMIN, True, True, True),
            (User.Role.ADMIN, True, False, False),
            (User.Role.ADMIN, False, True, False),
            (User.Role.STAFF, True, False, False),
            (User.Role.CUSTOMER, True, False, False),
        ]:
            with self.subTest(role=role, active=active, staff=staff):
                user = User(role=role, is_active=active, is_staff=staff)
                html = self.render_home(user)
                self.assertEqual('href="/admin/"' in html, expected)

    def test_bound_form_keeps_input_and_accessible_errors(self):
        class SampleForm(forms.Form):
            name = forms.CharField(help_text="Use your full name.")
            email = forms.EmailField()

        form = SampleForm({"name": '<script>alert("x")</script>', "email": "invalid"})
        self.assertFalse(form.is_valid())
        html = render_to_string("components/form_fields.html", {"form": form})
        self.assertIn('value="invalid"', html)
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="id_email_error"', html)
        self.assertIn('for="id_email"', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)

    def test_form_renders_non_field_and_hidden_errors(self):
        class SampleForm(forms.Form):
            record = forms.IntegerField(widget=forms.HiddenInput)

        form = SampleForm({"record": "invalid"})
        form.is_valid()
        form.add_error(None, "Please review this request.")
        html = render_to_string("components/form_fields.html", {"form": form})
        self.assertIn("Please review this request.", html)
        self.assertIn("Enter a whole number.", html)

    def test_empty_state_escapes_feature_supplied_copy(self):
        html = render_to_string(
            "components/empty_state.html", {"empty_title": "<script>alert(1)</script>"}
        )
        self.assertNotIn("<script>", html)
