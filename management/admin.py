from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Organization, Course, Batch, Student, Staff, Attendance, StaffAttendance, FeePayment, BehaviorNote, AdmissionApplication, Event, LeaveType, LeaveBalance, LeaveRequest, Expense, Payroll, PayrollComponent, SalaryComponent


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['org_name', 'slug', 'contact', 'license', 'created_at']
    search_fields = ['org_name', 'contact', 'slug']
    prepopulated_fields = {'slug': ('org_name',)}


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'organization', 'role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Organization Info', {'fields': ('organization', 'role', 'staff_profile')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Organization Info', {'fields': ('organization', 'role')}),
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'course_name', 'duration_value', 'duration_unit', 'fees', 'fee_period', 'organization', 'created_at']
    list_filter = ['fee_period', 'created_at', 'organization']
    search_fields = ['course_code', 'course_name']
    readonly_fields = ['course_code']


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['batch_code', 'batch_name', 'course', 'get_schedule_display', 'is_active', 'get_student_count']
    list_filter = ['is_active', 'course', 'days']
    search_fields = ['batch_code', 'batch_name', 'course__course_name']
    readonly_fields = ['batch_code']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'full_name', 'email', 'enrollment_date']
    list_filter = ['gender', 'enrollment_date']
    search_fields = ['student_id', 'full_name', 'email']
    readonly_fields = ['student_id']
    filter_horizontal = ['batches']


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'first_name', 'last_name', 'staff_role', 'department', 'working_hours_per_day', 'joining_date']
    list_filter = ['staff_role', 'department', 'gender']
    search_fields = ['staff_id', 'first_name', 'last_name', 'email']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'student', 'batch', 'status', 'marked_by', 'created_at']
    list_filter = ['status', 'date', 'batch']
    search_fields = ['student__full_name', 'student__student_id']


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'staff', 'status', 'hours', 'marked_by', 'created_at']
    list_filter = ['status', 'date', 'staff__staff_role']
    search_fields = ['staff__first_name', 'staff__last_name', 'staff__staff_id']


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'student', 'batch', 'amount', 'payment_date', 'payment_method']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['receipt_number', 'student__full_name']
    readonly_fields = ['receipt_number']


@admin.register(BehaviorNote)
class BehaviorNoteAdmin(admin.ModelAdmin):
    list_display = ['date', 'student', 'category', 'title', 'noted_by', 'created_at']
    list_filter = ['category', 'date', 'organization']
    search_fields = ['title', 'description', 'student__full_name']


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'phone', 'status', 'organization', 'created_at', 'reviewed_by']
    list_filter = ['status', 'organization', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'start_date', 'end_date', 'organization', 'created_by', 'created_at']
    list_filter = ['event_type', 'start_date', 'organization']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'days_per_year', 'period', 'is_paid', 'organization']
    list_filter = ['is_paid', 'period', 'organization']
    search_fields = ['name', 'code']


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'leave_type', 'year', 'allocated', 'used', 'organization']
    list_filter = ['year', 'leave_type', 'organization']
    search_fields = ['staff__first_name', 'staff__last_name', 'staff__staff_id']


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['staff', 'leave_type', 'start_date', 'end_date', 'days', 'status', 'requested_by', 'created_at']
    list_filter = ['status', 'leave_type', 'organization']
    search_fields = ['staff__first_name', 'staff__last_name', 'staff__staff_id']
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'amount', 'expense_date', 'payment_method', 'organization', 'created_by']
    list_filter = ['category', 'payment_method', 'expense_date', 'organization']
    search_fields = ['title', 'description', 'reference_number']
    readonly_fields = ['created_at', 'updated_at']


class PayrollComponentInline(admin.TabularInline):
    model = PayrollComponent
    extra = 0
    fields = ['name', 'component_type', 'amount', 'salary_component', 'notes']
    readonly_fields = []


@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'component_type', 'is_percentage', 'default_amount', 'is_active', 'organization']
    list_filter = ['component_type', 'is_active', 'organization']
    search_fields = ['name', 'code']


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['payroll_number', 'staff', 'month', 'year', 'net_salary', 'status', 'payment_date', 'payment_method', 'organization']
    list_filter = ['status', 'year', 'month', 'payment_method', 'organization']
    search_fields = ['payroll_number', 'staff__first_name', 'staff__last_name', 'staff__staff_id']
    readonly_fields = ['payroll_number', 'created_at', 'updated_at']
    inlines = [PayrollComponentInline]


@admin.register(PayrollComponent)
class PayrollComponentAdmin(admin.ModelAdmin):
    list_display = ['payroll', 'name', 'component_type', 'amount']
    list_filter = ['component_type']
    search_fields = ['name', 'payroll__payroll_number']


admin.site.register(User, CustomUserAdmin)
