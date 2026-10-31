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
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 == p2:
            # Construct a dummy user to run Django password validators against
            dummy = User(email=cleaned_data.get("email", ""), role=User.Role.CUSTOMER)
            validate_password(p1, user=dummy)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER  # hard requirement from the foundation contract
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class BrightloopAuthenticationForm(AuthenticationForm):
    """
    Thin wrapper over AuthenticationForm that normalizes the email field
    (stored in AuthenticationForm.username) to lower-case on clean.
    """

    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name")
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
        }
