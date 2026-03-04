import logging

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import Student, User
from .utils import normalize_phone

logger = logging.getLogger('management')


def parent_username(normalized_phone, org):
    """Generate org-scoped username for parent accounts: phone_orgId."""
    return f'{normalized_phone}_{org.id}'


@receiver(pre_save, sender=Student)
def capture_old_phone(sender, instance, **kwargs):
    """Capture the student's old phone before save to detect changes."""
    if instance.pk:
        try:
            old = Student.objects.get(pk=instance.pk)
            instance._old_phone = old.phone
        except Student.DoesNotExist:
            instance._old_phone = None
    else:
        instance._old_phone = None


@receiver(post_save, sender=Student)
def create_or_update_parent_account(sender, instance, created, **kwargs):
    """Auto-create a parent User account based on the student's phone number."""
    phone = instance.phone
    if not phone:
        return

    normalized = normalize_phone(phone)
    if not normalized or len(normalized) < 7:
        return

    org = instance.organization
    uname = parent_username(normalized, org)

    # Create or get parent user for this phone+org combination
    parent_user, user_created = User.objects.get_or_create(
        username=uname,
        defaults={
            'role': 'parent',
            'organization': org,
            'first_name': 'Parent',
            'last_name': normalized,
        }
    )

    if user_created:
        parent_user.set_password(normalized)
        parent_user.save(update_fields=['password'])
        logger.info(f'Created parent account for phone {normalized} in org {org}')

    # Handle phone number change: clean up old parent if no students left
    old_phone = getattr(instance, '_old_phone', None)
    if old_phone and old_phone != phone:
        old_normalized = normalize_phone(old_phone)
        if old_normalized and old_normalized != normalized:
            old_uname = parent_username(old_normalized, org)
            remaining = Student.objects.filter(
                organization=org,
                phone=old_phone,
            ).exclude(pk=instance.pk).exists()
            if not remaining:
                User.objects.filter(
                    username=old_uname,
                    role='parent',
                    organization=org,
                ).update(is_active=False)
                logger.info(f'Deactivated parent account {old_uname} (no students left)')


@receiver(post_delete, sender=Student)
def cleanup_parent_on_student_delete(sender, instance, **kwargs):
    """Deactivate parent account if no students remain with that phone."""
    phone = instance.phone
    if not phone:
        return

    normalized = normalize_phone(phone)
    if not normalized:
        return

    org = instance.organization
    uname = parent_username(normalized, org)
    remaining = Student.objects.filter(
        organization=org,
        phone=phone,
    ).exists()

    if not remaining:
        User.objects.filter(
            username=uname,
            role='parent',
            organization=org,
        ).update(is_active=False)
        logger.info(f'Deactivated parent account {uname} after student deletion')
