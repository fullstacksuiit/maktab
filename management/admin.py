from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Organization, Course, Batch, Student, Staff, Attendance, StaffAttendance, FeePayment


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['org_name', 'contact', 'license', 'created_at']
    search_fields = ['org_name', 'contact']


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
    list_display = ['student_id', 'first_name', 'last_name', 'email', 'enrollment_date']
    list_filter = ['gender', 'enrollment_date']
    search_fields = ['student_id', 'first_name', 'last_name', 'email']
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
    search_fields = ['student__first_name', 'student__last_name', 'student__student_id']


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'staff', 'status', 'hours', 'marked_by', 'created_at']
    list_filter = ['status', 'date', 'staff__staff_role']
    search_fields = ['staff__first_name', 'staff__last_name', 'staff__staff_id']


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'student', 'batch', 'amount', 'payment_date', 'payment_method']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['receipt_number', 'student__first_name', 'student__last_name']
    readonly_fields = ['receipt_number']


admin.site.register(User, CustomUserAdmin)
