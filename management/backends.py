import re

from django.contrib.auth.backends import ModelBackend

from .models import User
from .utils import normalize_phone


class PhoneOrUsernameBackend(ModelBackend):
    """Custom auth backend that normalizes phone-like usernames before authenticating.

    Allows parents to log in by typing their phone number in any format
    (e.g. '98765 43210', '+91-9876543210') and still match the normalized
    digits-only username stored in the database.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None

        # Check if the input looks like a phone number
        if re.match(r'^[\d\s\-\+\(\)]+$', username.strip()):
            normalized = normalize_phone(username)
            if normalized:
                try:
                    user = User.objects.select_related('organization').get(username=normalized)
                    if user.check_password(password) and self.user_can_authenticate(user):
                        return user
                except User.DoesNotExist:
                    pass

        # Fall back to exact username match (for admin/manager/staff)
        try:
            user = User.objects.select_related('organization').get(username=username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            pass

        return None
