import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email.strip())

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=email.strip().lower(), **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if (
            extra_fields["role"] != User.Role.ADMIN
            or not extra_fields["is_staff"]
            or not extra_fields["is_superuser"]
        ):
            raise ValueError("Superusers must have admin, staff, and superuser access.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STAFF = "STAFF", "Internal staff"
        CUSTOMER = "CUSTOMER", "Customer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=8, choices=Role.choices, default=Role.CUSTOMER)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_email_case_insensitive_unique"),
            models.CheckConstraint(
                condition=models.Q(role__in=["ADMIN", "STAFF", "CUSTOMER"]),
                name="accounts_role_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(is_staff=False, is_superuser=False) | models.Q(role="ADMIN"),
                name="accounts_privileged_flags_admin_only",
            ),
        ]

    def clean(self):
        super().clean()
        self.email = self.email.strip().lower()
        if (self.is_staff or self.is_superuser) and self.role != self.Role.ADMIN:
            raise ValidationError("Only administrators can access Django administration.")

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.email
