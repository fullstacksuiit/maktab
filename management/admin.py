from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Course, Student, Staff, Attendance, FeePayment


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'org_name', 'contact', 'license', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Organization Info', {'fields': ('org_name', 'address', 'contact', 'license')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Organization Info', {'fields': ('org_name', 'address', 'contact', 'license')}),
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_code', 'course_name', 'duration', 'fees', 'fee_period', 'created_by', 'created_at']
    list_filter = ['fee_period', 'created_at', 'created_by']
    search_fields = ['course_code', 'course_name']
    readonly_fields = ['course_code']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'first_name', 'last_name', 'email', 'enrollment_date']
    list_filter = ['gender', 'enrollment_date']
    search_fields = ['student_id', 'first_name', 'last_name', 'email']
    readonly_fields = ['student_id']
    filter_horizontal = ['courses']


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'first_name', 'last_name', 'role', 'department', 'joining_date']
    list_filter = ['role', 'department', 'gender']
    search_fields = ['staff_id', 'first_name', 'last_name', 'email']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'student', 'course', 'status', 'marked_by', 'created_at']
    list_filter = ['status', 'date', 'course']
    search_fields = ['student__first_name', 'student__last_name', 'student__student_id']


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'student', 'amount', 'payment_date', 'payment_method']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['receipt_number', 'student__first_name', 'student__last_name']
    readonly_fields = ['receipt_number']


admin.site.register(User, CustomUserAdmin)
