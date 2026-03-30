from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from management.models import (
    Organization, User, Course, Batch, Staff, Student, FeePayment,
)


class Command(BaseCommand):
    help = 'Set up local dev environment with an org, admin user, and sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-sample-data',
            action='store_true',
            help='Only create org and admin user, skip sample data',
        )

    def handle(self, *args, **options):
        # ── Organization ────────────────────────────────────────────────
        org, created = Organization.objects.get_or_create(
            slug='dev-maktab',
            defaults={
                'org_name': 'Dev Maktab',
                'address': '123 Development Street',
                'city': 'Rourkela',
                'state': 'Odisha',
                'contact': '9000000000',
                'currency_symbol': 'Rs.',
            },
        )
        self.stdout.write(f'Organization: {org.org_name} ({"created" if created else "exists"})')

        # ── Admin User ──────────────────────────────────────────────────
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'organization': org,
                'role': 'admin',
                'first_name': 'Admin',
            },
        )
        if created:
            admin.set_password('admin')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Admin user created — username: admin, password: admin'))
        else:
            admin.organization = org
            admin.role = 'admin'
            admin.save()
            self.stdout.write('Admin user: exists (org/role updated)')

        if options['no_sample_data']:
            self.stdout.write(self.style.SUCCESS('\nDone! Log in at /login/ with admin / admin'))
            return

        # ── Courses ─────────────────────────────────────────────────────
        quran, _ = Course.objects.get_or_create(
            course_code='QR001', organization=org,
            defaults={'course_name': 'Quran Recitation', 'fees': Decimal('500'), 'fee_period': 'monthly'},
        )
        arabic, _ = Course.objects.get_or_create(
            course_code='AR001', organization=org,
            defaults={'course_name': 'Arabic Grammar', 'fees': Decimal('400'), 'fee_period': 'monthly'},
        )
        islamic, _ = Course.objects.get_or_create(
            course_code='IS001', organization=org,
            defaults={'course_name': 'Islamic Studies', 'fees': Decimal('300'), 'fee_period': 'monthly'},
        )
        self.stdout.write(f'Courses: {quran}, {arabic}, {islamic}')

        # ── Batches ─────────────────────────────────────────────────────
        morning, _ = Batch.objects.get_or_create(
            batch_code='BTH001', organization=org,
            defaults={'batch_name': 'Morning Batch', 'course': quran, 'start_time': '06:00', 'end_time': '08:00', 'days': 'weekdays'},
        )
        evening, _ = Batch.objects.get_or_create(
            batch_code='BTH002', organization=org,
            defaults={'batch_name': 'Evening Batch', 'course': arabic, 'start_time': '16:00', 'end_time': '18:00', 'days': 'weekdays'},
        )
        weekend, _ = Batch.objects.get_or_create(
            batch_code='BTH003', organization=org,
            defaults={'batch_name': 'Weekend Batch', 'course': islamic, 'start_time': '09:00', 'end_time': '12:00', 'days': 'weekend'},
        )
        self.stdout.write(f'Batches: {morning}, {evening}, {weekend}')

        # ── Staff ───────────────────────────────────────────────────────
        teacher1, _ = Staff.objects.get_or_create(
            staff_id='STF001', organization=org,
            defaults={
                'first_name': 'Ahmed', 'last_name': 'Khan',
                'phone': '9100000001', 'date_of_birth': date(1985, 3, 15),
                'gender': 'M', 'address': '10 Teacher Colony',
                'staff_role': 'Teacher', 'department': 'Quran',
                'joining_date': date(2023, 1, 1), 'salary': Decimal('15000'),
            },
        )
        teacher2, _ = Staff.objects.get_or_create(
            staff_id='STF002', organization=org,
            defaults={
                'first_name': 'Fatima', 'last_name': 'Begum',
                'phone': '9100000002', 'date_of_birth': date(1990, 7, 20),
                'gender': 'F', 'address': '20 Teacher Colony',
                'staff_role': 'Teacher', 'department': 'Arabic',
                'joining_date': date(2023, 6, 1), 'salary': Decimal('12000'),
            },
        )
        morning.teachers.add(teacher1)
        evening.teachers.add(teacher2)
        weekend.teachers.add(teacher1)
        self.stdout.write(f'Staff: {teacher1.first_name}, {teacher2.first_name}')

        # ── Students ────────────────────────────────────────────────────
        today = date.today()
        students_data = [
            {'full_name': 'Ibrahim Ali', 'phone': '9200000001', 'guardian_name': 'Ali Khan', 'guardian_phone': '9200000011', 'gender': 'M'},
            {'full_name': 'Zainab Fatima', 'phone': '9200000002', 'guardian_name': 'Fatima Bibi', 'guardian_phone': '9200000012', 'gender': 'F'},
            {'full_name': 'Yusuf Ahmed', 'phone': '9200000003', 'guardian_name': 'Ahmed Hussain', 'guardian_phone': '9200000013', 'gender': 'M'},
            {'full_name': 'Aisha Begum', 'phone': '9200000004', 'guardian_name': 'Begum Jahan', 'guardian_phone': '9200000014', 'gender': 'F'},
            {'full_name': 'Omar Farooq', 'phone': '9200000005', 'guardian_name': 'Farooq Sahab', 'guardian_phone': '9200000015', 'gender': 'M',
             'is_orphan': True},
            {'full_name': 'Mariam Noor', 'phone': '9200000006', 'guardian_name': 'Noor Jahan', 'guardian_phone': '9200000016', 'gender': 'F',
             'discount_type': 'fixed', 'discount_value': Decimal('100')},
            {'full_name': 'Hassan Raza', 'phone': '9200000007', 'guardian_name': 'Raza Ali', 'guardian_phone': '9200000017', 'gender': 'M',
             'discount_type': 'percentage', 'discount_value': Decimal('20')},
            {'full_name': 'Khadija Bano', 'phone': '9200000008', 'guardian_name': 'Bano Begum', 'guardian_phone': '9200000018', 'gender': 'F'},
        ]

        created_students = []
        for i, data in enumerate(students_data):
            student, was_created = Student.objects.get_or_create(
                phone=data['phone'], organization=org,
                defaults={
                    'full_name': data['full_name'],
                    'guardian_name': data.get('guardian_name', ''),
                    'guardian_phone': data.get('guardian_phone', ''),
                    'gender': data['gender'],
                    'address': f'{(i+1)*10} Student Mohalla',
                    'enrollment_date': today - timedelta(days=90 + i * 15),
                    'is_orphan': data.get('is_orphan', False),
                    'discount_type': data.get('discount_type', ''),
                    'discount_value': data.get('discount_value', 0),
                },
            )
            created_students.append(student)

        # Assign batches — spread students across batches
        batch_assignments = [
            (0, [morning]),            # Ibrahim — morning only
            (1, [morning, evening]),   # Zainab — morning + evening
            (2, [evening]),            # Yusuf — evening only
            (3, [weekend]),            # Aisha — weekend only
            (4, [morning]),            # Omar (orphan) — morning
            (5, [morning]),            # Mariam (fixed discount) — morning
            (6, [evening, weekend]),   # Hassan (% discount) — evening + weekend
            (7, [morning, weekend]),   # Khadija — morning + weekend
        ]
        for idx, batches in batch_assignments:
            created_students[idx].batches.set(batches)

        self.stdout.write(f'Students: {len(created_students)} created/verified')

        # ── Fee Payments (a few sample ones) ────────────────────────────
        sample_payments = [
            (created_students[0], morning, Decimal('500'), today - timedelta(days=30)),
            (created_students[0], morning, Decimal('500'), today - timedelta(days=5)),
            (created_students[1], morning, Decimal('500'), today - timedelta(days=20)),
            (created_students[2], evening, Decimal('400'), today - timedelta(days=15)),
            (created_students[3], weekend, Decimal('300'), today - timedelta(days=10)),
        ]
        payment_count = 0
        for student, batch, amount, pay_date in sample_payments:
            _, was_created = FeePayment.objects.get_or_create(
                student=student, batch=batch, amount=amount,
                payment_date=pay_date, organization=org,
                defaults={
                    'payment_method': 'Cash',
                    'status': 'Approved',
                    'fee_month_from': pay_date.replace(day=1),
                    'fee_month_to': pay_date.replace(day=1),
                },
            )
            if was_created:
                payment_count += 1

        # One pending payment
        FeePayment.objects.get_or_create(
            student=created_students[7], batch=morning,
            amount=Decimal('500'), payment_date=today, organization=org,
            defaults={
                'payment_method': 'UPI',
                'status': 'Pending',
                'fee_month_from': today.replace(day=1),
                'fee_month_to': today.replace(day=1),
            },
        )

        self.stdout.write(f'Fee payments: {payment_count + 1} created/verified')

        # ── Summary ─────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Dev environment ready!'))
        self.stdout.write(f'  Login:    /login/')
        self.stdout.write(f'  Username: admin')
        self.stdout.write(f'  Password: admin')
        self.stdout.write('')
        self.stdout.write('  Sample data includes:')
        self.stdout.write('    3 courses, 3 batches, 2 teachers')
        self.stdout.write('    8 students (1 orphan, 1 fixed discount, 1 % discount)')
        self.stdout.write('    6 fee payments (5 approved, 1 pending)')
