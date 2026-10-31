from unittest.mock import patch

from django.db import OperationalError
from django.test import Client, TestCase


class PlatformTests(TestCase):
    def test_anonymous_admin_login_renders(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_home_is_explicit_about_unbuilt_features(self):
        response = self.client.get("/")
        self.assertContains(response, "still being developed")

    def test_database_health(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_database_failure_does_not_expose_details(self):
        with patch("core.views.connection.cursor", side_effect=OperationalError("secret details")):
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})

    def test_admin_login_requires_csrf(self):
        response = Client(enforce_csrf_checks=True).post(
            "/admin/login/", {"username": "admin@example.com", "password": "anything"}
        )
        self.assertEqual(response.status_code, 403)
