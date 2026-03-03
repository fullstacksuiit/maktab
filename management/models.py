from django.db import models, transaction
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import AbstractUser
from django.db.utils import IntegrityError
from django.utils.text import slugify
import uuid
import time


class Organization(models.Model):
    """Organization/Maktab that can have multiple users"""
    org_name = models.CharField(max_length=255, verbose_name="Organization Name")
    address = models.TextField(verbose_name="Address")
    city = models.CharField(max_length=100, blank=True, default='', verbose_name="City")
    state = models.CharField(max_length=100, blank=True, default='', verbose_name="State")
    pin_code = models.CharField(max_length=10, blank=True, default='', verbose_name="Pin Code")
    latitude = models.FloatField(blank=True, null=True, verbose_name="Latitude")
    longitude = models.FloatField(blank=True, null=True, verbose_name="Longitude")
    contact = models.CharField(max_length=20, verbose_name="Contact Number")
    license = models.CharField(max_length=100, blank=True, null=True, verbose_name="License")
    currency_symbol = models.CharField(max_length=10, default='Rs.', verbose_name="Currency Symbol")
    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bank Name")
    account_number = models.CharField(max_length=30, blank=True, null=True, verbose_name="Account Number")
    ifsc_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="IFSC Code")
    account_holder = models.CharField(max_length=100, blank=True, null=True, verbose_name="Account Holder Name")
    upi_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="UPI ID")
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="URL Slug")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['org_name']

    @property
    def full_address(self):
        parts = [self.address]
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.pin_code:
            parts.append(self.pin_code)
        return ', '.join(parts)

    def __str__(self):
        return self.org_name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.org_name) or 'org'
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class User(AbstractUser):
    """User with role-based access within an organization"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('parent', 'Parent'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
        verbose_name="Organization"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='staff',
        verbose_name="Role"
    )
    staff_profile = models.OneToOneField(
        'Staff',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_account',
        verbose_name="Linked Staff Profile"
    )

    def __str__(self):
        org_name = self.organization.org_name if self.organization else 'No Org'
        return f"{self.username} ({self.get_role_display()}) - {org_name}"

    def is_admin(self):
        return self.role == 'admin'

    def is_manager(self):
        return self.role == 'manager'

    def is_staff_role(self):
        return self.role == 'staff'

    def is_parent(self):
        return self.role == 'parent'

    def can_manage_users(self):
        return self.role == 'admin'

    def can_manage_settings(self):
        return self.role == 'admin'

    def can_create_edit(self):
        return self.role in ['admin', 'manager']

    def can_export(self):
        return self.role in ['admin', 'manager']


class Course(models.Model):
    FEE_PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    DURATION_UNIT_CHOICES = [
        ('months', 'Months'),
        ('years', 'Years'),
    ]

    course_name = models.CharField(max_length=255, verbose_name="Course Name")
    course_code = models.CharField(max_length=50, blank=True, verbose_name="Course Code")
    description = models.TextField(verbose_name="Description")
    duration_value = models.PositiveIntegerField(default=1, verbose_name="Duration Value")
    duration_unit = models.CharField(max_length=10, choices=DURATION_UNIT_CHOICES, default='months', verbose_name="Duration Unit")
    fees = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Course Fees")
    fee_period = models.CharField(max_length=20, choices=FEE_PERIOD_CHOICES, default='monthly', verbose_name="Fee Period")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='courses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'course_code']),
            models.Index(fields=['organization', 'course_name']),
            models.Index(fields=['fee_period']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['organization', 'course_code'], name='unique_course_code_per_org'),
        ]

    @property
    def duration_display(self):
        unit = self.get_duration_unit_display()
        if self.duration_value == 1:
            unit = unit.rstrip('s')
        return f"{self.duration_value} {unit}"

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

    def save(self, *args, **kwargs):
        if not self.course_code:
            for attempt in range(5):
                with transaction.atomic():
                    last_course = Course.objects.filter(organization=self.organization).select_for_update().order_by('-id').first()
                    if last_course and last_course.course_code.startswith('CRS'):
                        try:
                            last_number = int(last_course.course_code[3:])
                            new_number = last_number + 1
                        except ValueError:
                            new_number = 1
                    else:
                        new_number = 1
                    self.course_code = f"CRS{new_number:04d}"
                    try:
                        super().save(*args, **kwargs)
                        return
                    except IntegrityError:
                        if attempt == 4:
                            raise
                        time.sleep(0.1)
                        continue
        else:
            super().save(*args, **kwargs)


class Batch(models.Model):
    DAYS_CHOICES = [
        ('weekdays', 'Weekdays (Mon-Fri)'),
        ('weekend', 'Weekend (Sat-Sun)'),
        ('mwf', 'Mon, Wed, Fri'),
        ('tts', 'Tue, Thu, Sat'),
        ('daily', 'Daily'),
        ('custom', 'Custom'),
    ]

    batch_code = models.CharField(max_length=50, blank=True, verbose_name="Batch Code")
    batch_name = models.CharField(max_length=255, verbose_name="Batch Name")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='batches', verbose_name="Course")
    start_time = models.TimeField(verbose_name="Start Time", null=True, blank=True)
    end_time = models.TimeField(verbose_name="End Time", null=True, blank=True)
    days = models.CharField(max_length=20, choices=DAYS_CHOICES, default='weekdays', verbose_name="Days")
    max_capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name="Max Capacity")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='batches')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['course__course_name', 'batch_name']
        verbose_name_plural = "Batches"
        indexes = [
            models.Index(fields=['organization', 'batch_code']),
            models.Index(fields=['organization', 'course']),
            models.Index(fields=['is_active']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['organization', 'batch_code'], name='unique_batch_code_per_org'),
        ]

    def __str__(self):
        return f"{self.course.course_code} - {self.batch_name}"

    def save(self, *args, **kwargs):
        if not self.batch_code:
            for attempt in range(5):
                with transaction.atomic():
                    last_batch = Batch.objects.filter(organization=self.organization).select_for_update().order_by('-id').first()
                    if last_batch and last_batch.batch_code.startswith('BTH'):
                        try:
                            last_number = int(last_batch.batch_code[3:])
                            new_number = last_number + 1
                        except ValueError:
                            new_number = 1
                    else:
                        new_number = 1
                    self.batch_code = f"BTH{new_number:04d}"
                    try:
                        super().save(*args, **kwargs)
                        return
                    except IntegrityError:
                        if attempt == 4:
                            raise
                        time.sleep(0.1)
                        continue
        else:
            super().save(*args, **kwargs)

    def get_student_count(self):
        return self.students.count()

    def get_schedule_display(self):
        time_str = ""
        if self.start_time and self.end_time:
            time_str = f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"
        return f"{self.get_days_display()} {time_str}".strip()


class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    student_id = models.CharField(max_length=50, blank=True, verbose_name="Student ID")
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    email = models.EmailField(blank=True, default='', verbose_name="Email Address")
    phone = models.CharField(max_length=20, verbose_name="Phone Number")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Date of Birth")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Gender")
    address = models.TextField(verbose_name="Address")
    city = models.CharField(max_length=100, blank=True, default='', verbose_name="City")
    state = models.CharField(max_length=100, blank=True, default='', verbose_name="State")
    pin_code = models.CharField(max_length=10, blank=True, default='', verbose_name="Pin Code")
    is_orphan = models.BooleanField(default=False, verbose_name="Orphan")
    guardian_name = models.CharField(max_length=100, blank=True, default='', verbose_name="Guardian Name")
    guardian_phone = models.CharField(max_length=20, blank=True, default='', verbose_name="Guardian Phone")
    batches = models.ManyToManyField('Batch', related_name='students', verbose_name="Enrolled Batches", blank=True)
    enrollment_date = models.DateField(verbose_name="Enrollment Date")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='students')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'student_id']),
            models.Index(fields=['organization', 'first_name', 'last_name']),
            models.Index(fields=['organization', 'email']),
            models.Index(fields=['enrollment_date']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['organization', 'student_id'], name='unique_student_id_per_org'),
        ]

    @property
    def full_address(self):
        parts = [self.address]
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.pin_code:
            parts.append(self.pin_code)
        return ', '.join(parts)

    def __str__(self):
        return f"{self.student_id} - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.student_id:
            for attempt in range(5):
                with transaction.atomic():
                    last_student = Student.objects.filter(organization=self.organization).select_for_update().order_by('-id').first()
                    if last_student and last_student.student_id.startswith('STU'):
                        try:
                            last_number = int(last_student.student_id[3:])
                            new_number = last_number + 1
                        except ValueError:
                            new_number = 1
                    else:
                        new_number = 1
                    self.student_id = f"STU{new_number:04d}"
                    try:
                        super().save(*args, **kwargs)
                        return
                    except IntegrityError:
                        if attempt == 4:
                            raise
                        time.sleep(0.1)
                        continue
        else:
            super().save(*args, **kwargs)

    def get_total_fees(self):
        return self.batches.aggregate(total=Sum('course__fees'))['total'] or 0

    def get_enrolled_batches_list(self):
        if self.batches.exists():
            return ", ".join(f"{b.course.course_code} ({b.batch_name})" for b in self.batches.all())
        return "Not Enrolled"

    def get_total_paid(self):
        total = self.fee_payments.aggregate(Sum('amount'))['amount__sum']
        return total or 0

    def get_pending_fees(self):
        if self.is_orphan:
            return 0
        return self.get_total_fees() - self.get_total_paid()

    def get_attendance_percentage(self):
        result = self.attendances.aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(status__in=['Present', 'Late']))
        )
        if result['total'] == 0:
            return 0
        return round((result['present'] / result['total']) * 100, 1)


class Staff(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    ROLE_CHOICES = [
        ('Teacher', 'Teacher'),
        ('Administrator', 'Administrator'),
        ('Support', 'Support Staff'),
        ('Other', 'Other'),
    ]

    staff_id = models.CharField(max_length=50, verbose_name="Staff ID")
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    email = models.EmailField(blank=True, default='', verbose_name="Email Address")
    phone = models.CharField(max_length=20, verbose_name="Phone Number")
    date_of_birth = models.DateField(verbose_name="Date of Birth")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Gender")
    address = models.TextField(verbose_name="Address")
    city = models.CharField(max_length=100, blank=True, default='', verbose_name="City")
    state = models.CharField(max_length=100, blank=True, default='', verbose_name="State")
    pin_code = models.CharField(max_length=10, blank=True, default='', verbose_name="Pin Code")
    staff_role = models.CharField(max_length=50, choices=ROLE_CHOICES, verbose_name="Staff Role")
    department = models.CharField(max_length=100, verbose_name="Department")
    joining_date = models.DateField(verbose_name="Joining Date")
    salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monthly Salary")
    working_hours_per_day = models.DecimalField(max_digits=4, decimal_places=1, default=8.0, verbose_name="Working Hours/Day")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='staff_members')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Staff"
        indexes = [
            models.Index(fields=['organization', 'staff_id']),
            models.Index(fields=['organization', 'first_name', 'last_name']),
            models.Index(fields=['staff_role']),
            models.Index(fields=['department']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['organization', 'staff_id'], name='unique_staff_id_per_org'),
        ]

    @property
    def hourly_rate(self):
        """Derive hourly rate from monthly salary: salary / (working_hours_per_day x 26 working days)."""
        if self.working_hours_per_day and self.working_hours_per_day > 0:
            monthly_hours = self.working_hours_per_day * 26
            return round(float(self.salary) / float(monthly_hours), 2)
        return 0

    @property
    def full_address(self):
        parts = [self.address]
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.pin_code:
            parts.append(self.pin_code)
        return ', '.join(parts)

    def __str__(self):
        return f"{self.staff_id} - {self.first_name} {self.last_name}"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
        ('Excused', 'Excused'),
    ]

    date = models.DateField(verbose_name="Date")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='attendances', verbose_name="Batch", null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present', verbose_name="Status")
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_attendances', verbose_name="Marked By")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='attendances')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'date']),
            models.Index(fields=['organization', 'batch', 'date']),
            models.Index(fields=['student', 'status']),
        ]

    def __str__(self):
        return f"{self.student} - {self.batch} - {self.date} - {self.status}"


class BehaviorNote(models.Model):
    CATEGORY_CHOICES = [
        ('Homework', 'Homework'),
        ('Discipline', 'Discipline'),
        ('Participation', 'Participation'),
        ('Academic', 'Academic Performance'),
        ('General', 'General'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='behavior_notes')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='General', verbose_name="Category")
    title = models.CharField(max_length=200, verbose_name="Title")
    description = models.TextField(verbose_name="Description")
    date = models.DateField(verbose_name="Date")
    noted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='behavior_notes', verbose_name="Noted By")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='behavior_notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'student']),
            models.Index(fields=['organization', 'date']),
        ]

    def __str__(self):
        return f"{self.student} - {self.title} ({self.date})"


class StaffAttendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
        ('Excused', 'Excused'),
    ]

    date = models.DateField(verbose_name="Date")
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='attendances')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present', verbose_name="Status")
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_staff_attendances', verbose_name="Marked By")
    hours = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, verbose_name="Hours Worked")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='staff_attendances')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'date']),
            models.Index(fields=['staff', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['organization', 'staff', 'date'], name='unique_staff_attendance_per_day'),
        ]

    @property
    def earnings(self):
        if self.hours and self.staff.hourly_rate:
            return round(float(self.hours) * self.staff.hourly_rate, 2)
        return 0

    def __str__(self):
        return f"{self.staff} - {self.date} - {self.status}"


class FeePayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Online', 'Online'),
        ('UPI', 'UPI'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_payments')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='fee_payments', verbose_name="Batch")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount")
    payment_date = models.DateField(verbose_name="Payment Date")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash', verbose_name="Payment Method")
    receipt_number = models.CharField(max_length=50, blank=True, verbose_name="Receipt Number")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='fee_payments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'payment_date']),
            models.Index(fields=['organization', 'receipt_number']),
            models.Index(fields=['student', 'payment_date']),
            models.Index(fields=['payment_method']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['organization', 'receipt_number'], name='unique_receipt_number_per_org'),
        ]

    def __str__(self):
        return f"{self.receipt_number} - {self.student} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            for attempt in range(5):
                with transaction.atomic():
                    last_payment = FeePayment.objects.filter(organization=self.organization).select_for_update().order_by('-id').first()
                    if last_payment and last_payment.receipt_number.startswith('RCP'):
                        try:
                            last_number = int(last_payment.receipt_number[3:])
                            new_number = last_number + 1
                        except ValueError:
                            new_number = 1
                    else:
                        new_number = 1
                    self.receipt_number = f"RCP{new_number:04d}"
                    try:
                        super().save(*args, **kwargs)
                        return
                    except IntegrityError:
                        if attempt == 4:
                            raise
                        time.sleep(0.1)
                        continue
        else:
            super().save(*args, **kwargs)


class AdmissionApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    phone = models.CharField(max_length=20, verbose_name="Phone Number")
    email = models.EmailField(blank=True, default='', verbose_name="Email Address")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Date of Birth")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Gender")
    address = models.TextField(verbose_name="Address")
    city = models.CharField(max_length=100, blank=True, default='', verbose_name="City")
    state = models.CharField(max_length=100, blank=True, default='', verbose_name="State")
    pin_code = models.CharField(max_length=10, blank=True, default='', verbose_name="Pin Code")
    notes = models.TextField(blank=True, default='', verbose_name="Notes / Message")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    rejection_reason = models.TextField(blank=True, default='', verbose_name="Rejection Reason")

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='admission_applications'
    )
    student = models.OneToOneField(
        'Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='admission_application', verbose_name="Created Student"
    )
    reviewed_by = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_applications', verbose_name="Reviewed By"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Reviewed At")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_status_display()})"


class Event(models.Model):
    EVENT_TYPE_CHOICES = [
        ('holiday', 'Holiday'),
        ('exam', 'Exam'),
        ('meeting', 'Meeting'),
        ('parent_teacher', 'Parent-Teacher Day'),
        ('fee_deadline', 'Fee Deadline'),
        ('other', 'Other'),
    ]

    EVENT_TYPE_COLORS = {
        'holiday': '#ef4444',
        'exam': '#f59e0b',
        'meeting': '#3b82f6',
        'parent_teacher': '#8b5cf6',
        'fee_deadline': '#f97316',
        'other': '#6b7280',
    }

    title = models.CharField(max_length=200, verbose_name="Title")
    description = models.TextField(blank=True, default='', verbose_name="Description")
    event_type = models.CharField(
        max_length=20, choices=EVENT_TYPE_CHOICES, default='other',
        verbose_name="Event Type"
    )
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_events', verbose_name="Created By"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'title']
        indexes = [
            models.Index(fields=['organization', 'start_date']),
            models.Index(fields=['organization', 'end_date']),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_date})"

    @property
    def color(self):
        return self.EVENT_TYPE_COLORS.get(self.event_type, '#6b7280')

    @property
    def is_multi_day(self):
        return self.start_date != self.end_date

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date cannot be before start date.'})


class LeaveType(models.Model):
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    name = models.CharField(max_length=100, verbose_name="Leave Type")
    code = models.CharField(max_length=10, verbose_name="Code")
    days_per_year = models.PositiveIntegerField(default=0, verbose_name="Default Days")
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='yearly', verbose_name="Period")
    is_paid = models.BooleanField(default=True, verbose_name="Is Paid")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='leave_types')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'code'], name='unique_leave_type_code_per_org'),
        ]

    @property
    def yearly_allocation(self):
        """Return the total yearly allocation based on period."""
        if self.period == 'monthly':
            return self.days_per_year * 12
        return self.days_per_year

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveBalance(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='balances')
    year = models.PositiveIntegerField(verbose_name="Year")
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="Allocated Days")
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="Used Days")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='leave_balances')

    class Meta:
        ordering = ['leave_type__name']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'staff', 'leave_type', 'year'],
                name='unique_leave_balance_per_staff_type_year'
            ),
        ]

    @property
    def remaining(self):
        return float(self.allocated) - float(self.used)

    def __str__(self):
        return f"{self.staff} - {self.leave_type.code} ({self.year}): {self.remaining} remaining"


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")
    days = models.DecimalField(max_digits=5, decimal_places=1, verbose_name="Total Days")
    half_day = models.BooleanField(default=False, verbose_name="Half Day")
    reason = models.TextField(verbose_name="Reason")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    rejection_reason = models.TextField(blank=True, default='', verbose_name="Rejection Reason")

    requested_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='leave_requests_made', verbose_name="Requested By"
    )
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='leave_requests_reviewed', verbose_name="Reviewed By"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Reviewed At")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='leave_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'staff', 'start_date']),
        ]

    def __str__(self):
        return f"{self.staff} - {self.leave_type.code} ({self.start_date} to {self.end_date})"


def create_default_leave_types(organization):
    """Create default leave types for a new organization."""
    defaults = [
        ('Casual Leave', 'CL', 12, True),
        ('Sick Leave', 'SL', 12, True),
        ('Earned Leave', 'EL', 15, True),
        ('Unpaid Leave', 'UL', 0, False),
    ]
    for name, code, days, is_paid in defaults:
        LeaveType.objects.get_or_create(
            organization=organization, code=code,
            defaults={'name': name, 'days_per_year': days, 'is_paid': is_paid}
        )


def ensure_leave_balances(staff, year):
    """Ensure LeaveBalance records exist for all leave types for this staff and year."""
    org = staff.organization
    leave_types = LeaveType.objects.filter(organization=org)
    for lt in leave_types:
        LeaveBalance.objects.get_or_create(
            organization=org, staff=staff, leave_type=lt, year=year,
            defaults={'allocated': lt.yearly_allocation}
        )


class PunchRecord(models.Model):
    PUNCH_TYPE_CHOICES = [
        ('in', 'Punch In'),
        ('out', 'Punch Out'),
    ]

    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='punch_records')
    punch_type = models.CharField(max_length=3, choices=PUNCH_TYPE_CHOICES, verbose_name="Punch Type")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp")
    date = models.DateField(verbose_name="Date")
    notes = models.CharField(max_length=255, blank=True, default='', verbose_name="Notes")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='punch_records')

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['organization', 'staff', 'date']),
            models.Index(fields=['organization', 'date']),
        ]

    def __str__(self):
        return f"{self.staff} - {self.get_punch_type_display()} at {self.timestamp}"


class SalaryComponent(models.Model):
    COMPONENT_TYPE_CHOICES = [
        ('earning', 'Earning / Allowance'),
        ('deduction', 'Deduction'),
    ]

    name = models.CharField(max_length=100, verbose_name="Component Name")
    code = models.CharField(max_length=20, verbose_name="Code")
    component_type = models.CharField(max_length=10, choices=COMPONENT_TYPE_CHOICES, verbose_name="Type")
    is_percentage = models.BooleanField(default=False, verbose_name="Is Percentage of Base Salary")
    default_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Default Amount / Percentage")
    description = models.CharField(max_length=255, blank=True, default='', verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='salary_components')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['component_type', 'name']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'code'], name='unique_salary_component_code_per_org'),
        ]

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.get_component_type_display()}"


class Payroll(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processed', 'Processed'),
        ('paid', 'Paid'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Online', 'Online'),
        ('UPI', 'UPI'),
    ]

    payroll_number = models.CharField(max_length=50, blank=True, verbose_name="Payroll Number")
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='payrolls')
    month = models.PositiveIntegerField(verbose_name="Month")
    year = models.PositiveIntegerField(verbose_name="Year")
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Base Salary")
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Earnings")
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total Deductions")
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Net Salary")
    days_present = models.PositiveIntegerField(default=0, verbose_name="Days Present")
    days_absent = models.PositiveIntegerField(default=0, verbose_name="Days Absent")
    days_late = models.PositiveIntegerField(default=0, verbose_name="Days Late")
    total_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0, verbose_name="Total Hours Worked")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name="Status")
    payment_date = models.DateField(null=True, blank=True, verbose_name="Payment Date")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, default='', verbose_name="Payment Method")
    notes = models.TextField(blank=True, default='', verbose_name="Notes")
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_payrolls')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='payrolls')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', '-month', 'staff__first_name']
        indexes = [
            models.Index(fields=['organization', 'year', 'month']),
            models.Index(fields=['organization', 'staff']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['organization', 'staff', 'month', 'year'], name='unique_payroll_per_staff_month'),
        ]

    def __str__(self):
        return f"{self.payroll_number} - {self.staff} ({self.month}/{self.year})"

    def recalculate_totals(self):
        """Recalculate total_earnings, total_deductions, and net_salary from components."""
        from django.db.models import Sum
        components = self.components.all()
        self.total_earnings = self.base_salary + (
            components.filter(component_type='earning').aggregate(total=Sum('amount'))['total'] or 0
        )
        self.total_deductions = (
            components.filter(component_type='deduction').aggregate(total=Sum('amount'))['total'] or 0
        )
        self.net_salary = self.total_earnings - self.total_deductions
        self.save(update_fields=['total_earnings', 'total_deductions', 'net_salary', 'updated_at'])

    def save(self, *args, **kwargs):
        if not self.payroll_number:
            for attempt in range(5):
                with transaction.atomic():
                    last = Payroll.objects.filter(organization=self.organization).select_for_update().order_by('-id').first()
                    if last and last.payroll_number.startswith('PAY'):
                        try:
                            num = int(last.payroll_number[3:]) + 1
                        except ValueError:
                            num = 1
                    else:
                        num = 1
                    self.payroll_number = f"PAY{num:04d}"
                    try:
                        super().save(*args, **kwargs)
                        return
                    except IntegrityError:
                        if attempt == 4:
                            raise
                        time.sleep(0.1)
                        continue
        else:
            super().save(*args, **kwargs)


class PayrollComponent(models.Model):
    COMPONENT_TYPE_CHOICES = [
        ('earning', 'Earning / Allowance'),
        ('deduction', 'Deduction'),
    ]

    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='components')
    salary_component = models.ForeignKey(SalaryComponent, on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_usages')
    name = models.CharField(max_length=100, verbose_name="Component Name")
    component_type = models.CharField(max_length=10, choices=COMPONENT_TYPE_CHOICES, verbose_name="Type")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount")
    notes = models.CharField(max_length=255, blank=True, default='', verbose_name="Notes")

    class Meta:
        ordering = ['component_type', 'name']

    def __str__(self):
        return f"{self.name}: {self.amount}"


def create_default_salary_components(organization):
    """Create default salary components for a new organization."""
    defaults = [
        ('Late Deduction', 'LATE', 'deduction', False, 50),
        ('Leave Without Pay', 'LWP', 'deduction', False, 0),
        ('Transport Allowance', 'TA', 'earning', False, 500),
        ('Performance Bonus', 'BONUS', 'earning', False, 0),
    ]
    for name, code, comp_type, is_pct, amount in defaults:
        SalaryComponent.objects.get_or_create(
            organization=organization, code=code,
            defaults={
                'name': name,
                'component_type': comp_type,
                'is_percentage': is_pct,
                'default_amount': amount,
            }
        )
