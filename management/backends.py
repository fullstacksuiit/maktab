import re

from django.contrib.auth.backends import ModelBackend

from .models import User, Staff
from .utils import normalize_phone


class PhoneOrUsernameBackend(ModelBackend):
    """Custom auth backend that supports multiple login methods:

    1. Staff login: staff_id + phone number
    2. Parent login: phone number (normalized) + password
    3. Standard login: username + password (admin/manager)
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None

        # --- Staff login: match staff_id, verify phone as password ---
        normalized_password = normalize_phone(password) if password else ''
        try:
            staff = Staff.objects.select_related('organization').get(staff_id=username)
            staff_phone = normalize_phone(staff.phone)
            if staff_phone and normalized_password == staff_phone:
                user = self._get_or_create_staff_user(staff)
                if user and self.user_can_authenticate(user):
                    return user
        except Staff.DoesNotExist:
            pass
        except Staff.MultipleObjectsReturned:
            # staff_id is unique per org but not globally; try all matches
            for staff in Staff.objects.select_related('organization').filter(staff_id=username):
                staff_phone = normalize_phone(staff.phone)
                if staff_phone and normalized_password == staff_phone:
                    user = self._get_or_create_staff_user(staff)
                    if user and self.user_can_authenticate(user):
                        return user

        # --- Parent login: phone number + password ---
        if re.match(r'^[\d\s\-\+\(\)]+$', username.strip()):
            normalized = normalize_phone(username)
            if normalized:
                try:
                    user = User.objects.select_related('organization').get(username=normalized)
                    if user.check_password(password) and self.user_can_authenticate(user):
                        return user
                except User.DoesNotExist:
                    pass

        # --- Standard login: username + password (admin/manager) ---
        try:
            user = User.objects.select_related('organization').get(username=username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            pass

        return None

    def _get_or_create_staff_user(self, staff):
        """Get the linked User account for a Staff member, or create one."""
        try:
            user = staff.user_account
            if user:
                return user
        except User.DoesNotExist:
            pass

        # Auto-create a User account for this staff member
        user = User(
            username=staff.staff_id,
            first_name=staff.first_name,
            last_name=staff.last_name,
            email=staff.email,
            role='staff',
            organization=staff.organization,
            staff_profile=staff,
        )
        user.set_password(normalize_phone(staff.phone))
        user.save()
        return user
