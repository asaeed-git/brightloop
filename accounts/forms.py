"""Public-facing account forms. Internal Django admin forms live in admin.py."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password

from .models import User


class SignupForm(forms.ModelForm):
    """
    Public signup form; always creates a CUSTOMER account.

    Role is never taken from submitted data; it is fixed server-side in save().
    Password is validated against all configured AUTH_PASSWORD_VALIDATORS so the
    same rules apply here as in the Django admin form.
    """

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=("At least 9 characters, with uppercase, lowercase, and a special character."),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Enter the same password again to confirm.",
    )

    class Meta:
        model = User
        fields = ("email",)
        widgets = {
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        # Normalize first so the uniqueness check matches the DB constraint
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1", "")
        p2 = self.cleaned_data.get("password2", "")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("The two passwords did not match.")
        return p2

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password1")
        if password:
            # Build a throwaway User instance so similarity validators can compare
            # the password against the email.  Role is always CUSTOMER.
            candidate = User(email=cleaned.get("email", ""), role=User.Role.CUSTOMER)
            validate_password(password, candidate)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        # Unconditionally set CUSTOMER regardless of anything in POST data.
        user.role = User.Role.CUSTOMER
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class BrightloopAuthenticationForm(AuthenticationForm):
    """
    Thin wrapper around Django's built-in login form.

    Sets autocomplete attributes for browsers and normalizes the submitted
    email to lowercase before authentication so case-variant logins work.
    Django's authenticate() also calls get_by_natural_key() which uses
    iexact, but normalizing here ensures the displayed value is canonical.
    """

    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class BrightloopPasswordResetForm(PasswordResetForm):
    """
    Thin wrapper that normalizes the submitted email and sets autocomplete.

    Django's PasswordResetForm.save() only sends mail if the email matches
    an active account, so non-existent addresses produce the same success
    response without revealing whether the account exists.
    """

    email = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class BrightloopSetPasswordForm(SetPasswordForm):
    """
    Thin wrapper that sets autocomplete attributes on the reset-confirm form.
    """

    new_password1 = forms.CharField(
        label="New password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=("At least 9 characters, with uppercase, lowercase, and a special character."),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
