"""Shared server checks; role-aware navigation is not authorization."""

from django.core.exceptions import PermissionDenied

from .models import User


def require_roles(user, *roles):
    if not user.is_authenticated or not user.is_active or user.role not in roles:
        raise PermissionDenied("You do not have access to this action.")


def scope_to_customer(queryset, user, customer_field="customer_id"):
    """Domain records reference accounts.User as customer; fail closed by default."""
    require_roles(user, User.Role.ADMIN, User.Role.STAFF, User.Role.CUSTOMER)
    if user.role == User.Role.CUSTOMER:
        return queryset.filter(**{customer_field: user.pk})
    return queryset
