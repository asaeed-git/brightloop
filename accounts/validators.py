from django.core.exceptions import ValidationError


class BrightloopPasswordValidator:
    def validate(self, password, user=None):
        if not (
            len(password) >= 9
            and any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(not c.isalnum() and not c.isspace() for c in password)
        ):
            raise ValidationError(self.get_help_text(), code="password_requirements")

    def get_help_text(self):
        return (
            "Use at least nine characters, including an uppercase letter, "
            "a lowercase letter, and a special character."
        )
