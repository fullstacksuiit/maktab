from django.core.management.base import BaseCommand

from management.models import Student, User
from management.utils import normalize_phone


class Command(BaseCommand):
    help = 'Create parent accounts for all existing students based on phone numbers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-id', type=int,
            help='Only process a specific organization'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be created without actually creating'
        )

    def handle(self, *args, **options):
        org_id = options.get('org_id')
        dry_run = options.get('dry_run', False)

        students = Student.objects.select_related('organization').all()
        if org_id:
            students = students.filter(organization_id=org_id)

        created_count = 0
        skipped_count = 0

        # Track (org_id, normalized_phone) pairs we've already processed
        seen = set()

        for student in students:
            if not student.phone:
                continue

            normalized = normalize_phone(student.phone)
            if not normalized or len(normalized) < 7:
                self.stdout.write(
                    f'  SKIP: {student} - phone "{student.phone}" too short after normalization'
                )
                skipped_count += 1
                continue

            key = (student.organization_id, normalized)
            if key in seen:
                continue
            seen.add(key)

            # Check if parent user already exists
            existing = User.objects.filter(
                username=normalized, role='parent', organization=student.organization
            ).exists()
            if existing:
                self.stdout.write(f'  EXISTS: {normalized} for org {student.organization}')
                skipped_count += 1
                continue

            # Check if username is taken by a non-parent user
            if User.objects.filter(username=normalized).exists():
                self.stdout.write(
                    f'  CONFLICT: username {normalized} already exists as non-parent user'
                )
                skipped_count += 1
                continue

            if dry_run:
                self.stdout.write(f'  WOULD CREATE: {normalized} for org {student.organization}')
            else:
                User.objects.create_user(
                    username=normalized,
                    password=normalized,
                    role='parent',
                    organization=student.organization,
                    first_name='Parent',
                    last_name=normalized,
                )
                self.stdout.write(f'  CREATED: {normalized} for org {student.organization}')
            created_count += 1

        action = 'Would create' if dry_run else 'Created'
        self.stdout.write(self.style.SUCCESS(
            f'\n{action} {created_count} parent account(s). Skipped {skipped_count}.'
        ))
