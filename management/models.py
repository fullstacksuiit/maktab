from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    org_name = models.CharField(max_length=255, verbose_name="Organization Name")
    address = models.TextField(verbose_name="Address")
    contact = models.CharField(max_length=20, verbose_name="Contact Number")
    license = models.CharField(max_length=100, blank=True, null=True, verbose_name="License")
    currency_symbol = models.CharField(max_length=10, default='Rs.', verbose_name="Currency Symbol")

    def __str__(self):
        return f"{self.username} - {self.org_name}"


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
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

    def save(self, *args, **kwargs):
        if not self.course_code:
            last_course = Course.objects.order_by('-id').first()
            if last_course and last_course.course_code.startswith('CRS'):
                try:
                    last_number = int(last_course.course_code[3:])
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1
            self.course_code = f"CRS{new_number:04d}"
        super().save(*args, **kwargs)


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
    courses = models.ManyToManyField(Course, related_name='students', verbose_name="Enrolled Courses", blank=True)
    enrollment_date = models.DateField(verbose_name="Enrollment Date")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='students')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student_id} - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.student_id:
            last_student = Student.objects.order_by('-id').first()
            if last_student and last_student.student_id.startswith('STU'):
                try:
                    last_number = int(last_student.student_id[3:])
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1
            self.student_id = f"STU{new_number:04d}"
        super().save(*args, **kwargs)

    def get_total_fees(self):
        return sum(course.fees for course in self.courses.all())

    def get_enrolled_courses_list(self):
        return ", ".join(course.course_code for course in self.courses.all()) if self.courses.exists() else "Not Enrolled"

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
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, verbose_name="Role")
    department = models.CharField(max_length=100, verbose_name="Department")
    joining_date = models.DateField(verbose_name="Joining Date")
    salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Salary")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='staff_members')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Staff"

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
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendances')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present', verbose_name="Status")
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_attendances', verbose_name="Marked By")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = ['date', 'student', 'course']

    def __str__(self):
        return f"{self.student} - {self.course} - {self.date} - {self.status}"


class FeePayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Online', 'Online'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_payments')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='fee_payments', verbose_name="Course")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount")
    payment_date = models.DateField(verbose_name="Payment Date")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash', verbose_name="Payment Method")
    receipt_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name="Receipt Number")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fee_payments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"{self.receipt_number} - {self.student} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            last_payment = FeePayment.objects.order_by('-id').first()
            if last_payment and last_payment.receipt_number.startswith('RCP'):
                try:
                    last_number = int(last_payment.receipt_number[3:])
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1
            self.receipt_number = f"RCP{new_number:04d}"
        super().save(*args, **kwargs)
