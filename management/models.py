from django.db import models, transaction
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser
from django.db.utils import IntegrityError
import time


class Organization(models.Model):
    """Organization/Maktab that can have multiple users"""
    org_name = models.CharField(max_length=255, verbose_name="Organization Name")
    address = models.TextField(verbose_name="Address")
    contact = models.CharField(max_length=20, verbose_name="Contact Number")
    license = models.CharField(max_length=100, blank=True, null=True, verbose_name="License")
    currency_symbol = models.CharField(max_length=10, default='Rs.', verbose_name="Currency Symbol")
    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bank Name")
    account_number = models.CharField(max_length=30, blank=True, null=True, verbose_name="Account Number")
    ifsc_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="IFSC Code")
    account_holder = models.CharField(max_length=100, blank=True, null=True, verbose_name="Account Holder Name")
    upi_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="UPI ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['org_name']

    def __str__(self):
        return self.org_name


class User(AbstractUser):
    """User with role-based access within an organization"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
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

    course_name = models.CharField(max_length=255, verbose_name="Course Name")
    course_code = models.CharField(max_length=50, unique=True, blank=True, verbose_name="Course Code")
    description = models.TextField(verbose_name="Description")
    duration = models.CharField(max_length=100, verbose_name="Duration")
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

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

    def save(self, *args, **kwargs):
        if not self.course_code:
            for attempt in range(5):
                with transaction.atomic():
                    last_course = Course.objects.select_for_update().order_by('-id').first()
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

    batch_code = models.CharField(max_length=50, unique=True, blank=True, verbose_name="Batch Code")
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

    def __str__(self):
        return f"{self.course.course_code} - {self.batch_name}"

    def save(self, *args, **kwargs):
        if not self.batch_code:
            for attempt in range(5):
                with transaction.atomic():
                    last_batch = Batch.objects.select_for_update().order_by('-id').first()
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

    student_id = models.CharField(max_length=50, unique=True, blank=True, verbose_name="Student ID")
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    email = models.EmailField(verbose_name="Email Address")
    phone = models.CharField(max_length=20, verbose_name="Phone Number")
    date_of_birth = models.DateField(verbose_name="Date of Birth")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Gender")
    address = models.TextField(verbose_name="Address")
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

    def __str__(self):
        return f"{self.student_id} - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.student_id:
            for attempt in range(5):
                with transaction.atomic():
                    last_student = Student.objects.select_for_update().order_by('-id').first()
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
        return sum(batch.course.fees for batch in self.batches.all())

    def get_enrolled_batches_list(self):
        if self.batches.exists():
            return ", ".join(f"{b.course.course_code} ({b.batch_name})" for b in self.batches.all())
        return "Not Enrolled"

    def get_total_paid(self):
        total = self.fee_payments.aggregate(Sum('amount'))['amount__sum']
        return total or 0

    def get_pending_fees(self):
        return self.get_total_fees() - self.get_total_paid()

    def get_attendance_percentage(self):
        total = self.attendances.count()
        if total == 0:
            return 0
        present = self.attendances.filter(status__in=['Present', 'Late']).count()
        return round((present / total) * 100, 1)


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

    staff_id = models.CharField(max_length=50, unique=True, verbose_name="Staff ID")
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    email = models.EmailField(verbose_name="Email Address")
    phone = models.CharField(max_length=20, verbose_name="Phone Number")
    date_of_birth = models.DateField(verbose_name="Date of Birth")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Gender")
    address = models.TextField(verbose_name="Address")
    staff_role = models.CharField(max_length=50, choices=ROLE_CHOICES, verbose_name="Staff Role")
    department = models.CharField(max_length=100, verbose_name="Department")
    joining_date = models.DateField(verbose_name="Joining Date")
    salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Salary")
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
            models.Index(fields=['student', 'status']),
        ]

    def __str__(self):
        return f"{self.student} - {self.batch} - {self.date} - {self.status}"


class FeePayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Online', 'Online'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_payments')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='fee_payments', verbose_name="Batch")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount")
    payment_date = models.DateField(verbose_name="Payment Date")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash', verbose_name="Payment Method")
    receipt_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name="Receipt Number")
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

    def __str__(self):
        return f"{self.receipt_number} - {self.student} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            for attempt in range(5):
                with transaction.atomic():
                    last_payment = FeePayment.objects.select_for_update().order_by('-id').first()
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
