
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Q, Subquery, OuterRef, DecimalField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from datetime import date, datetime
import json
import logging
import re

logger = logging.getLogger('management')

from .forms import (SignUpForm, LoginForm, CourseForm, BatchForm, StudentForm, StaffForm,
                    AttendanceFilterForm, FeePaymentForm, SettingsForm, InviteUserForm, UserEditForm)
from .models import User, Organization, Course, Batch, Student, Staff, Attendance, FeePayment
from .decorators import role_required, admin_required, manager_or_admin_required, parent_required, internal_user_required
from .indian_cities import CITY_DATA
from .hijri_dates import get_upcoming_islamic_dates


def get_org(request):
    """Helper to get the current user's organization."""
    return request.user.organization


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            # Send welcome email
            try:
                html_message = render_to_string('management/emails/welcome.html', {
                    'username': user.username,
                    'org_name': user.organization.org_name,
                })
                send_mail(
                    subject='Welcome to Maktab!',
                    message=f'Assalamu Alaikum {user.username}, your account for {user.organization.org_name} has been created successfully.',
                    from_email=None,  # uses DEFAULT_FROM_EMAIL
                    recipient_list=[user.email],
                    html_message=html_message,
                )
            except Exception as e:
                logger.error(f'Failed to send welcome email to {user.email}: {e}')

            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignUpForm()
    return render(request, 'management/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                display_name = user.first_name or username
                messages.success(request, f'Assalamu Alaikum, {display_name}!')
                if user.is_parent():
                    return redirect('parent_dashboard')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'management/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required(login_url='login')
@internal_user_required
def dashboard_view(request):
    org = get_org(request)

    # Single aggregate query for all counts instead of 4 separate COUNT queries
    from django.db.models import Value, BooleanField
    counts = Organization.objects.filter(pk=org.pk).aggregate(
        total_courses=Count('courses', distinct=True),
        total_batches=Count('batches', filter=Q(batches__is_active=True), distinct=True),
        total_students=Count('students', distinct=True),
        total_staff=Count('staff_members', distinct=True),
    )
    total_courses = counts['total_courses']
    total_batches = counts['total_batches']
    total_students = counts['total_students']
    total_staff = counts['total_staff']

    # Single query for revenue (used for both total_revenue and pending calc)
    total_revenue = FeePayment.objects.filter(
        organization=org
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Calculate total pending fees based on batches
    total_fees_subquery = Student.objects.filter(
        organization=org
    ).annotate(
        student_total_fees=Coalesce(Sum('batches__course__fees'), 0, output_field=DecimalField())
    ).aggregate(total=Sum('student_total_fees'))['total'] or 0

    total_pending = total_fees_subquery - total_revenue

    # Single query for today's attendance with conditional count
    today = date.today()
    today_attendance = Attendance.objects.filter(organization=org, date=today).aggregate(
        today_total=Count('id'),
        today_present=Count('id', filter=Q(status__in=['Present', 'Late'])),
    )
    today_total = today_attendance['today_total']
    today_present = today_attendance['today_present']

    recent_students = Student.objects.filter(organization=org).prefetch_related('batches__course').order_by('-created_at')[:5]
    recent_payments = FeePayment.objects.filter(organization=org).select_related('student', 'batch__course').order_by('-created_at')[:5]

    # Get batches with student count for quick attendance
    batches_for_attendance = Batch.objects.filter(organization=org, is_active=True).select_related('course').annotate(
        student_count=Count('students')
    ).order_by('course__course_name', 'batch_name')[:6]

    # Payment method breakdown
    payment_stats = FeePayment.objects.filter(organization=org).values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    cash_total = 0
    bank_total = 0
    online_total = 0
    for stat in payment_stats:
        if stat['payment_method'] == 'Cash':
            cash_total = stat['total'] or 0
        elif stat['payment_method'] == 'Bank Transfer':
            bank_total = stat['total'] or 0
        elif stat['payment_method'] == 'Online':
            online_total = stat['total'] or 0

    context = {
        'total_courses': total_courses,
        'total_batches': total_batches,
        'total_students': total_students,
        'total_staff': total_staff,
        'total_revenue': total_revenue,
        'total_pending': total_pending,
        'today_total': today_total,
        'today_present': today_present,
        'recent_students': recent_students,
        'recent_payments': recent_payments,
        'batches_for_attendance': batches_for_attendance,
        'cash_total': cash_total,
        'bank_total': bank_total,
        'online_total': online_total,
        'islamic_dates': get_upcoming_islamic_dates(),
    }
    return render(request, 'management/dashboard_main.html', context)


# ─── Course Views ────────────────────────────────────────────────────────────

@login_required(login_url='login')
@internal_user_required
def course_list(request):
    org = get_org(request)
    courses_qs = Course.objects.filter(organization=org).annotate(
        student_count=Count('batches__students', distinct=True)
    )

    # Server-side search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        courses_qs = courses_qs.filter(
            Q(course_name__icontains=search_query) |
            Q(course_code__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(courses_qs, 20)
    page_number = request.GET.get('page')
    courses = paginator.get_page(page_number)
    return render(request, 'management/course_list.html', {
        'courses': courses,
        'search_query': search_query,
    })


@login_required(login_url='login')
@manager_or_admin_required
def course_add(request):
    org = get_org(request)
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.organization = org
            course.save()
            messages.success(request, 'Course added successfully!')
            return redirect('course_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseForm()
    return render(request, 'management/course_form.html', {'form': form, 'action': 'Add'})


@login_required(login_url='login')
@manager_or_admin_required
def course_edit(request, pk):
    org = get_org(request)
    course = get_object_or_404(Course, pk=pk, organization=org)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully!')
            return redirect('course_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseForm(instance=course)
    return render(request, 'management/course_form.html', {'form': form, 'action': 'Edit'})


@login_required(login_url='login')
@manager_or_admin_required
@require_POST
def course_delete(request, pk):
    org = get_org(request)
    course = get_object_or_404(Course, pk=pk, organization=org)
    course_name = course.course_name
    course.delete()
    messages.success(request, f'Course "{course_name}" deleted successfully!')
    return redirect('course_list')


# ─── Batch Views ─────────────────────────────────────────────────────────────

@login_required(login_url='login')
@internal_user_required
def batch_list(request):
    org = get_org(request)
    batches_qs = Batch.objects.filter(organization=org).select_related('course').annotate(
        student_count=Count('students')
    )

    # Server-side search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        batches_qs = batches_qs.filter(
            Q(batch_name__icontains=search_query) |
            Q(batch_code__icontains=search_query) |
            Q(course__course_name__icontains=search_query) |
            Q(course__course_code__icontains=search_query)
        )

    # Filter by course
    course_id = request.GET.get('course')
    if course_id:
        batches_qs = batches_qs.filter(course_id=course_id)

    # Filter by active status
    status = request.GET.get('status')
    if status == 'active':
        batches_qs = batches_qs.filter(is_active=True)
    elif status == 'inactive':
        batches_qs = batches_qs.filter(is_active=False)

    courses = Course.objects.filter(organization=org)

    paginator = Paginator(batches_qs, 20)
    page_number = request.GET.get('page')
    batches = paginator.get_page(page_number)
    return render(request, 'management/batch_list.html', {
        'batches': batches,
        'courses': courses,
        'search_query': search_query,
        'selected_course': course_id,
        'selected_status': status,
    })


@login_required(login_url='login')
@manager_or_admin_required
def batch_add(request):
    org = get_org(request)
    if request.method == 'POST':
        form = BatchForm(request.POST)
        form.fields['course'].queryset = Course.objects.filter(organization=org)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.organization = org
            batch.save()
            messages.success(request, 'Batch added successfully!')
            return redirect('batch_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BatchForm()
        form.fields['course'].queryset = Course.objects.filter(organization=org)

        # Pre-select course if provided
        course_id = request.GET.get('course')
        if course_id:
            form.initial['course'] = course_id

    return render(request, 'management/batch_form.html', {'form': form, 'action': 'Add'})


@login_required(login_url='login')
@manager_or_admin_required
def batch_edit(request, pk):
    org = get_org(request)
    batch = get_object_or_404(Batch, pk=pk, organization=org)
    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch)
        form.fields['course'].queryset = Course.objects.filter(organization=org)
        if form.is_valid():
            form.save()
            messages.success(request, 'Batch updated successfully!')
            return redirect('batch_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BatchForm(instance=batch)
        form.fields['course'].queryset = Course.objects.filter(organization=org)
    return render(request, 'management/batch_form.html', {'form': form, 'action': 'Edit'})


@login_required(login_url='login')
@manager_or_admin_required
@require_POST
def batch_delete(request, pk):
    org = get_org(request)
    batch = get_object_or_404(Batch, pk=pk, organization=org)
    batch_name = batch.batch_name
    batch.delete()
    messages.success(request, f'Batch "{batch_name}" deleted successfully!')
    return redirect('batch_list')


# ─── Student Views ───────────────────────────────────────────────────────────

@login_required(login_url='login')
@internal_user_required
def student_list(request):
    org = get_org(request)
    students_qs = Student.objects.filter(organization=org).prefetch_related('batches__course', 'fee_payments')

    # Server-side search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        students_qs = students_qs.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(student_id__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    paginator = Paginator(students_qs, 20)
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)
    return render(request, 'management/student_list.html', {
        'students': students,
        'search_query': search_query,
    })


@login_required(login_url='login')
@manager_or_admin_required
def student_add(request):
    org = get_org(request)
    if request.method == 'POST':
        form = StudentForm(request.POST)
        form.fields['batches'].queryset = Batch.objects.filter(organization=org, is_active=True).select_related('course')
        if form.is_valid():
            student = form.save(commit=False)
            student.organization = org
            student.save()
            form.save_m2m()
            messages.success(request, 'Student added successfully!')
            return redirect('student_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentForm()
        form.fields['batches'].queryset = Batch.objects.filter(organization=org, is_active=True).select_related('course')
    return render(request, 'management/student_form.html', {'form': form, 'action': 'Add'})


@login_required(login_url='login')
@manager_or_admin_required
def student_edit(request, pk):
    org = get_org(request)
    student = get_object_or_404(Student, pk=pk, organization=org)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        form.fields['batches'].queryset = Batch.objects.filter(organization=org, is_active=True).select_related('course')
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully!')
            return redirect('student_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentForm(instance=student)
        form.fields['batches'].queryset = Batch.objects.filter(organization=org, is_active=True).select_related('course')
    return render(request, 'management/student_form.html', {'form': form, 'action': 'Edit'})


@login_required(login_url='login')
@manager_or_admin_required
@require_POST
def student_delete(request, pk):
    org = get_org(request)
    student = get_object_or_404(Student, pk=pk, organization=org)
    student_name = f"{student.first_name} {student.last_name}"
    student.delete()
    messages.success(request, f'Student "{student_name}" deleted successfully!')
    return redirect('student_list')


@login_required(login_url='login')
@internal_user_required
def student_detail(request, pk):
    org = get_org(request)
    student = get_object_or_404(Student, pk=pk, organization=org)
    attendances = Attendance.objects.filter(
        student=student, organization=org
    ).order_by('-date')[:20]
    fee_payments = FeePayment.objects.filter(
        student=student, organization=org
    ).order_by('-payment_date')

    context = {
        'student': student,
        'attendances': attendances,
        'fee_payments': fee_payments,
        'attendance_percentage': student.get_attendance_percentage(),
        'total_paid': student.get_total_paid(),
        'pending_fees': student.get_pending_fees(),
    }
    return render(request, 'management/student_detail.html', context)


@login_required(login_url='login')
@internal_user_required
def student_fee_history(request, pk):
    org = get_org(request)
    student = get_object_or_404(Student.objects.prefetch_related('batches__course'), pk=pk, organization=org)
    payments = FeePayment.objects.filter(student=student, organization=org).select_related('batch__course')
    context = {
        'student': student,
        'payments': payments,
        'total_paid': student.get_total_paid(),
        'total_fees': student.get_total_fees(),
        'pending_fees': student.get_pending_fees(),
    }
    return render(request, 'management/student_fee_history.html', context)


# ─── Staff Views ─────────────────────────────────────────────────────────────

@login_required(login_url='login')
@internal_user_required
def staff_list(request):
    org = get_org(request)
    staff_qs = Staff.objects.filter(organization=org)

    # Server-side search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        staff_qs = staff_qs.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(staff_id__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(staff_role__icontains=search_query) |
            Q(department__icontains=search_query)
        )

    paginator = Paginator(staff_qs, 20)
    page_number = request.GET.get('page')
    staff_members = paginator.get_page(page_number)
    return render(request, 'management/staff_list.html', {
        'staff_members': staff_members,
        'search_query': search_query,
    })


@login_required(login_url='login')
@manager_or_admin_required
def staff_add(request):
    org = get_org(request)
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            staff = form.save(commit=False)
            staff.organization = org
            staff.save()
            messages.success(request, 'Staff member added successfully!')
            return redirect('staff_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffForm()
    return render(request, 'management/staff_form.html', {'form': form, 'action': 'Add'})


@login_required(login_url='login')
@manager_or_admin_required
def staff_edit(request, pk):
    org = get_org(request)
    staff = get_object_or_404(Staff, pk=pk, organization=org)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member updated successfully!')
            return redirect('staff_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffForm(instance=staff)
    return render(request, 'management/staff_form.html', {'form': form, 'action': 'Edit'})


@login_required(login_url='login')
@manager_or_admin_required
@require_POST
def staff_delete(request, pk):
    org = get_org(request)
    staff = get_object_or_404(Staff, pk=pk, organization=org)
    staff_name = f"{staff.first_name} {staff.last_name}"
    staff.delete()
    messages.success(request, f'Staff member "{staff_name}" deleted successfully!')
    return redirect('staff_list')


@login_required(login_url='login')
@internal_user_required
def staff_detail(request, pk):
    org = get_org(request)
    staff = get_object_or_404(Staff, pk=pk, organization=org)
    return render(request, 'management/staff_detail.html', {'staff': staff})


# ─── Attendance Views ────────────────────────────────────────────────────────

@login_required(login_url='login')
@internal_user_required
def attendance_list(request):
    org = get_org(request)
    attendances = Attendance.objects.filter(organization=org).select_related('student', 'batch__course')

    batch_id = request.GET.get('batch')
    filter_date = request.GET.get('date')
    if batch_id:
        attendances = attendances.filter(batch_id=batch_id)
    if filter_date:
        attendances = attendances.filter(date=filter_date)

    batches = Batch.objects.filter(organization=org, is_active=True).select_related('course')

    paginator = Paginator(attendances, 50)
    page_number = request.GET.get('page')
    attendances_page = paginator.get_page(page_number)

    context = {
        'attendances': attendances_page,
        'batches': batches,
        'selected_batch': batch_id,
        'selected_date': filter_date,
    }
    return render(request, 'management/attendance_list.html', context)


@login_required(login_url='login')
@internal_user_required
def attendance_mark(request):
    org = get_org(request)
    if request.method == 'POST':
        batch_id = request.POST.get('batch')
        attendance_date = request.POST.get('date')
        batch = get_object_or_404(Batch, pk=batch_id, organization=org)

        students = list(batch.students.filter(organization=org))
        existing = {
            a.student_id: a for a in Attendance.objects.filter(
                date=attendance_date, batch=batch, organization=org,
                student__in=students
            )
        }
        to_create = []
        to_update = []
        for student in students:
            status = request.POST.get(f'status_{student.pk}', 'Absent')
            notes = request.POST.get(f'notes_{student.pk}', '')
            if student.pk in existing:
                att = existing[student.pk]
                att.status = status
                att.marked_by = request.user
                att.notes = notes
                to_update.append(att)
            else:
                to_create.append(Attendance(
                    date=attendance_date, student=student, batch=batch,
                    organization=org, status=status, marked_by=request.user, notes=notes,
                ))
        if to_create:
            Attendance.objects.bulk_create(to_create)
        if to_update:
            Attendance.objects.bulk_update(to_update, ['status', 'marked_by', 'notes'])
        marked_count = len(students)

        messages.success(request, f'Attendance marked for {marked_count} students!')
        return redirect('attendance_list')

    form = AttendanceFilterForm()
    form.fields['batch'].queryset = Batch.objects.filter(organization=org, is_active=True).select_related('course')

    students = None
    selected_batch = None
    selected_date = None
    existing_attendance = {}

    if request.GET.get('batch') and request.GET.get('date'):
        try:
            selected_batch = Batch.objects.select_related('course').get(pk=request.GET['batch'], organization=org)
            selected_date = request.GET['date']
            students = selected_batch.students.filter(organization=org)

            existing = Attendance.objects.filter(
                batch=selected_batch, date=selected_date, organization=org
            )
            existing_attendance = {a.student_id: a for a in existing}

            form.initial = {'batch': selected_batch.pk, 'date': selected_date}
        except Batch.DoesNotExist:
            pass

    context = {
        'form': form,
        'students': students,
        'selected_batch': selected_batch,
        'selected_date': selected_date,
        'existing_attendance': existing_attendance,
    }
    return render(request, 'management/attendance_mark.html', context)


@login_required(login_url='login')
@internal_user_required
def quick_attendance(request, batch_id):
    """Quick attendance view - tap to toggle attendance status"""
    org = get_org(request)
    batch = get_object_or_404(Batch.objects.select_related('course'), pk=batch_id, organization=org)
    today = date.today()
    attendance_date = request.GET.get('date', str(today))

    students = batch.students.filter(organization=org).order_by('first_name', 'last_name')

    # Get existing attendance for this date
    existing = Attendance.objects.filter(
        batch=batch, date=attendance_date, organization=org
    )
    attendance_map = {a.student_id: a.status for a in existing}

    # Prepare students with their attendance status
    students_data = []
    for student in students:
        students_data.append({
            'student': student,
            'status': attendance_map.get(student.pk, None),  # None means not marked
        })

    context = {
        'batch': batch,
        'students_data': students_data,
        'attendance_date': attendance_date,
        'today': str(today),
        'present_count': sum(1 for s in students_data if s['status'] == 'Present'),
        'absent_count': sum(1 for s in students_data if s['status'] == 'Absent'),
        'total_count': len(students_data),
    }
    return render(request, 'management/quick_attendance.html', context)


@login_required(login_url='login')
@internal_user_required
@require_POST
def toggle_attendance(request):
    """AJAX endpoint to toggle attendance status"""
    org = get_org(request)
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        batch_id = data.get('batch_id')
        attendance_date = data.get('date')
        new_status = data.get('status')  # Present, Absent, or None (to delete)

        student = get_object_or_404(Student, pk=student_id, organization=org)
        batch = get_object_or_404(Batch, pk=batch_id, organization=org)

        if new_status in ['Present', 'Absent', 'Late', 'Excused']:
            attendance, created = Attendance.objects.update_or_create(
                date=attendance_date,
                student=student,
                batch=batch,
                organization=org,
                defaults={
                    'status': new_status,
                    'marked_by': request.user,
                }
            )
            return JsonResponse({
                'success': True,
                'status': new_status,
                'message': f'{student.first_name} marked as {new_status}'
            })
        else:
            # Delete the attendance record if status is None/empty
            Attendance.objects.filter(
                date=attendance_date,
                student=student,
                batch=batch,
                organization=org
            ).delete()
            return JsonResponse({
                'success': True,
                'status': None,
                'message': f'{student.first_name} attendance cleared'
            })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required(login_url='login')
@internal_user_required
@require_POST
def mark_all_present(request):
    """AJAX endpoint to mark all students present for a batch on a date"""
    org = get_org(request)
    try:
        data = json.loads(request.body)
        batch_id = data.get('batch_id')
        attendance_date = data.get('date')

        batch = get_object_or_404(Batch, pk=batch_id, organization=org)
        students = list(batch.students.filter(organization=org))
        existing = {
            a.student_id: a for a in Attendance.objects.filter(
                date=attendance_date, batch=batch, organization=org,
                student__in=students
            )
        }
        to_create = []
        to_update = []
        for student in students:
            if student.pk in existing:
                att = existing[student.pk]
                att.status = 'Present'
                att.marked_by = request.user
                to_update.append(att)
            else:
                to_create.append(Attendance(
                    date=attendance_date, student=student, batch=batch,
                    organization=org, status='Present', marked_by=request.user,
                ))
        if to_create:
            Attendance.objects.bulk_create(to_create)
        if to_update:
            Attendance.objects.bulk_update(to_update, ['status', 'marked_by'])
        count = len(students)

        return JsonResponse({
            'success': True,
            'count': count,
            'message': f'All {count} students marked as Present'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required(login_url='login')
@internal_user_required
@require_POST
def mark_all_absent(request):
    """AJAX endpoint to mark all students absent for a batch on a date"""
    org = get_org(request)
    try:
        data = json.loads(request.body)
        batch_id = data.get('batch_id')
        attendance_date = data.get('date')

        batch = get_object_or_404(Batch, pk=batch_id, organization=org)
        students = list(batch.students.filter(organization=org))
        existing = {
            a.student_id: a for a in Attendance.objects.filter(
                date=attendance_date, batch=batch, organization=org,
                student__in=students
            )
        }
        to_create = []
        to_update = []
        for student in students:
            if student.pk in existing:
                att = existing[student.pk]
                att.status = 'Absent'
                att.marked_by = request.user
                to_update.append(att)
            else:
                to_create.append(Attendance(
                    date=attendance_date, student=student, batch=batch,
                    organization=org, status='Absent', marked_by=request.user,
                ))
        if to_create:
            Attendance.objects.bulk_create(to_create)
        if to_update:
            Attendance.objects.bulk_update(to_update, ['status', 'marked_by'])
        count = len(students)

        return JsonResponse({
            'success': True,
            'count': count,
            'message': f'All {count} students marked as Absent'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ─── Fee Payment Views ───────────────────────────────────────────────────────

@login_required(login_url='login')
@internal_user_required
def fee_payment_list(request):
    org = get_org(request)
    payments_qs = FeePayment.objects.filter(organization=org).select_related('student', 'batch__course')

    # Server-side search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        payments_qs = payments_qs.filter(
            Q(receipt_number__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query) |
            Q(batch__course__course_name__icontains=search_query) |
            Q(batch__batch_name__icontains=search_query)
        )

    # Payment method filter
    selected_method = request.GET.get('method', '').strip()
    if selected_method:
        payments_qs = payments_qs.filter(payment_method=selected_method)

    paginator = Paginator(payments_qs, 20)
    page_number = request.GET.get('page')
    payments = paginator.get_page(page_number)
    return render(request, 'management/fee_payment_list.html', {
        'payments': payments,
        'search_query': search_query,
        'selected_method': selected_method,
    })


@login_required(login_url='login')
@manager_or_admin_required
def fee_payment_add(request):
    org = get_org(request)
    if request.method == 'POST':
        form = FeePaymentForm(request.POST)
        form.fields['student'].queryset = Student.objects.filter(organization=org)
        form.fields['batch'].queryset = Batch.objects.filter(organization=org, is_active=True).select_related('course')
        if form.is_valid():
            payment = form.save(commit=False)
            payment.organization = org
            payment.save()
            messages.success(request, f'Payment recorded! Receipt: {payment.receipt_number}')
            return redirect('fee_payment_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeePaymentForm()
        form.fields['student'].queryset = Student.objects.filter(organization=org)
        form.fields['batch'].queryset = Batch.objects.filter(organization=org, is_active=True).select_related('course')

        student_id = request.GET.get('student')
        if student_id:
            form.initial['student'] = student_id

    return render(request, 'management/fee_payment_add.html', {'form': form, 'action': 'Record'})


@login_required(login_url='login')
@manager_or_admin_required
def fee_payment_edit(request, pk):
    org = get_org(request)
    payment = get_object_or_404(FeePayment, pk=pk, organization=org)
    if request.method == 'POST':
        form = FeePaymentForm(request.POST, instance=payment)
        form.fields['student'].queryset = Student.objects.filter(organization=org)
        form.fields['batch'].queryset = Batch.objects.filter(organization=org, is_active=True).select_related('course')
        if form.is_valid():
            form.save()
            messages.success(request, f'Payment #{payment.receipt_number} updated!')
            return redirect('fee_payment_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeePaymentForm(instance=payment)
        form.fields['student'].queryset = Student.objects.filter(organization=org)
        form.fields['batch'].queryset = Batch.objects.filter(organization=org, is_active=True).select_related('course')
    return render(request, 'management/fee_payment_add.html', {'form': form, 'action': 'Edit'})


@login_required(login_url='login')
@manager_or_admin_required
@require_POST
def fee_payment_delete(request, pk):
    org = get_org(request)
    payment = get_object_or_404(FeePayment, pk=pk, organization=org)
    receipt_number = payment.receipt_number
    payment.delete()
    messages.success(request, f'Payment record #{receipt_number} deleted successfully!')
    return redirect('fee_payment_list')


@login_required(login_url='login')
@internal_user_required
def print_receipt(request, pk):
    org = get_org(request)
    payment = get_object_or_404(FeePayment, pk=pk, organization=org)
    return render(request, 'management/receipt_print.html', {'payment': payment, 'organization': org})


# ─── API: Cities by State ────────────────────────────────────────────────────

def get_cities_for_state(request):
    """Return cities for a given state as JSON (used by dynamic dropdowns)."""
    state = request.GET.get('state', '')
    cities = sorted(CITY_DATA.get(state, {}).keys())
    return JsonResponse({'cities': cities})


# ─── Settings ────────────────────────────────────────────────────────────────

@login_required(login_url='login')
@admin_required
def settings_view(request):
    org = get_org(request)
    if request.method == 'POST':
        form = SettingsForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated successfully!')
            return redirect('settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SettingsForm(instance=org)
    return render(request, 'management/settings.html', {'form': form})


# ─── User Management Views ───────────────────────────────────────────────────

@login_required(login_url='login')
@admin_required
def user_list(request):
    """List all users in the organization."""
    org = get_org(request)
    users = User.objects.filter(organization=org).order_by('-date_joined')
    return render(request, 'management/user_list.html', {'users': users})


@login_required(login_url='login')
@admin_required
def user_invite(request):
    """Invite a new user to the organization."""
    org = get_org(request)
    if request.method == 'POST':
        form = InviteUserForm(request.POST, organization=org)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" created successfully!')
            return redirect('user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = InviteUserForm(organization=org)
    return render(request, 'management/user_invite.html', {'form': form})


@login_required(login_url='login')
@admin_required
def user_edit(request, pk):
    """Edit a user's role and details."""
    org = get_org(request)
    user = get_object_or_404(User, pk=pk, organization=org)

    # Prevent editing yourself via this form
    if user == request.user:
        messages.error(request, 'You cannot edit your own account here.')
        return redirect('user_list')

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{user.username}" updated successfully!')
            return redirect('user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'management/user_edit.html', {'form': form, 'edit_user': user})


@login_required(login_url='login')
@admin_required
@require_POST
def user_delete(request, pk):
    """Delete a user from the organization."""
    org = get_org(request)
    user = get_object_or_404(User, pk=pk, organization=org)

    # Prevent deleting yourself
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')

    username = user.username
    user.delete()
    messages.success(request, f'User "{username}" deleted successfully!')
    return redirect('user_list')


# ─── Excel Exports ───────────────────────────────────────────────────────────

@login_required(login_url='login')
@manager_or_admin_required
def export_students_excel(request):
    org = get_org(request)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students"

    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="0D6B4E", end_color="0D6B4E", fill_type="solid")

    headers = ['Student ID', 'First Name', 'Last Name', 'Email', 'Phone',
               'Gender', 'Date of Birth', 'Enrollment Date', 'Enrolled Batches', 'Total Fees']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    students = Student.objects.filter(organization=org).prefetch_related('batches__course')
    for row, student in enumerate(students, 2):
        ws.cell(row=row, column=1, value=student.student_id)
        ws.cell(row=row, column=2, value=student.first_name)
        ws.cell(row=row, column=3, value=student.last_name)
        ws.cell(row=row, column=4, value=student.email)
        ws.cell(row=row, column=5, value=student.phone)
        ws.cell(row=row, column=6, value=student.get_gender_display())
        ws.cell(row=row, column=7, value=str(student.date_of_birth))
        ws.cell(row=row, column=8, value=str(student.enrollment_date))
        ws.cell(row=row, column=9, value=student.get_enrolled_batches_list())
        ws.cell(row=row, column=10, value=float(student.get_total_fees()))

    for col in ws.columns:
        max_length = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 40)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="students.xlsx"'
    wb.save(response)
    return response


@login_required(login_url='login')
@manager_or_admin_required
def export_staff_excel(request):
    org = get_org(request)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Staff"

    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="0D6B4E", end_color="0D6B4E", fill_type="solid")

    headers = ['Staff ID', 'First Name', 'Last Name', 'Email', 'Phone',
               'Role', 'Department', 'Joining Date', 'Salary']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    staff_members = Staff.objects.filter(organization=org)
    for row, staff in enumerate(staff_members, 2):
        ws.cell(row=row, column=1, value=staff.staff_id)
        ws.cell(row=row, column=2, value=staff.first_name)
        ws.cell(row=row, column=3, value=staff.last_name)
        ws.cell(row=row, column=4, value=staff.email)
        ws.cell(row=row, column=5, value=staff.phone)
        ws.cell(row=row, column=6, value=staff.staff_role)
        ws.cell(row=row, column=7, value=staff.department)
        ws.cell(row=row, column=8, value=str(staff.joining_date))
        ws.cell(row=row, column=9, value=float(staff.salary))

    for col in ws.columns:
        max_length = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 40)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="staff.xlsx"'
    wb.save(response)
    return response


@login_required(login_url='login')
@manager_or_admin_required
def export_attendance_excel(request):
    org = get_org(request)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance"

    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="0D6B4E", end_color="0D6B4E", fill_type="solid")

    headers = ['Date', 'Student ID', 'Student Name', 'Course', 'Batch', 'Status', 'Notes']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    attendances = Attendance.objects.filter(organization=org).select_related('student', 'batch__course')
    for row, att in enumerate(attendances, 2):
        ws.cell(row=row, column=1, value=str(att.date))
        ws.cell(row=row, column=2, value=att.student.student_id)
        ws.cell(row=row, column=3, value=f"{att.student.first_name} {att.student.last_name}")
        ws.cell(row=row, column=4, value=att.batch.course.course_name if att.batch else "N/A")
        ws.cell(row=row, column=5, value=att.batch.batch_name if att.batch else "N/A")
        ws.cell(row=row, column=6, value=att.status)
        ws.cell(row=row, column=7, value=att.notes or '')

    for col in ws.columns:
        max_length = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 40)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="attendance.xlsx"'
    wb.save(response)
    return response


@login_required(login_url='login')
@manager_or_admin_required
def export_fee_payments_excel(request):
    org = get_org(request)
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Fee Payments"

    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="0D6B4E", end_color="0D6B4E", fill_type="solid")

    headers = ['Receipt Number', 'Student ID', 'Student Name', 'Course', 'Batch', 'Amount', 'Date', 'Method', 'Remarks']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    payments = FeePayment.objects.filter(organization=org).select_related('student', 'batch__course')
    for row, payment in enumerate(payments, 2):
        ws.cell(row=row, column=1, value=payment.receipt_number)
        ws.cell(row=row, column=2, value=payment.student.student_id)
        ws.cell(row=row, column=3, value=f"{payment.student.first_name} {payment.student.last_name}")
        ws.cell(row=row, column=4, value=payment.batch.course.course_name if payment.batch else "N/A")
        ws.cell(row=row, column=5, value=payment.batch.batch_name if payment.batch else "N/A")
        ws.cell(row=row, column=6, value=float(payment.amount))
        ws.cell(row=row, column=7, value=str(payment.payment_date))
        ws.cell(row=row, column=8, value=payment.payment_method)
        ws.cell(row=row, column=9, value=payment.notes or '')

    for col in ws.columns:
        max_length = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 40)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="fee_payments.xlsx"'
    wb.save(response)
    return response


# ─── Student Import ──────────────────────────────────────────────────────────

@login_required(login_url='login')
@manager_or_admin_required
def download_student_template(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student Import"

    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="0D6B4E", end_color="0D6B4E", fill_type="solid")

    headers = [
        'Student ID', 'First Name', 'Last Name', 'Email', 'Phone',
        'Gender', 'Date of Birth', 'Address', 'City', 'State',
        'Pin Code', 'Enrollment Date', 'Batches'
    ]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    # Sample data row
    sample = [
        '', 'Ahmed', 'Khan', 'ahmed@example.com', '9876543210',
        'M', '2005-03-15', '123 Main Street', 'Mumbai', 'Maharashtra',
        '400001', '2024-01-15', 'BTH0001, BTH0002'
    ]
    hint_font = Font(italic=True, color="808080")
    for col, value in enumerate(sample, 1):
        cell = ws.cell(row=2, column=col, value=value)
        cell.font = hint_font

    # Instructions sheet
    ins = wb.create_sheet("Instructions")
    instructions = [
        ['Column', 'Required', 'Format / Notes'],
        ['Student ID', 'No', 'Leave blank for auto-generation. If provided, must be unique.'],
        ['First Name', 'Yes', 'Text, max 100 characters'],
        ['Last Name', 'Yes', 'Text, max 100 characters'],
        ['Email', 'No', 'Valid email format (e.g. name@example.com)'],
        ['Phone', 'Yes', '7-20 characters. Digits, spaces, +, -, ( ) allowed'],
        ['Gender', 'Yes', 'M or Male, F or Female, O or Other'],
        ['Date of Birth', 'No', 'YYYY-MM-DD format. Cannot be in the future.'],
        ['Address', 'Yes', 'Street / area text'],
        ['City', 'No', 'Text'],
        ['State', 'No', 'Text'],
        ['Pin Code', 'No', 'Text, max 10 characters'],
        ['Enrollment Date', 'Yes', 'YYYY-MM-DD format. Cannot be in the future.'],
        ['Batches', 'No', 'Comma-separated batch codes (e.g. BTH0001, BTH0002)'],
    ]
    for row_idx, row_data in enumerate(instructions, 1):
        for col_idx, value in enumerate(row_data, 1):
            cell = ins.cell(row=row_idx, column=col_idx, value=value)
            if row_idx == 1:
                cell.font = header_font
                cell.fill = header_fill

    for sheet in [ws, ins]:
        for col in sheet.columns:
            max_length = max(len(str(cell.value or '')) for cell in col)
            sheet.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="student_import_template.xlsx"'
    wb.save(response)
    return response


@login_required(login_url='login')
@manager_or_admin_required
def import_students(request):
    org = get_org(request)
    context = {'errors': [], 'success_count': 0, 'has_results': False}

    if request.method == 'POST':
        file = request.FILES.get('excel_file')
        if not file:
            messages.error(request, 'Please select an Excel file to upload.')
            return render(request, 'management/student_import.html', context)

        if not file.name.endswith('.xlsx'):
            messages.error(request, 'Please upload a valid .xlsx file.')
            return render(request, 'management/student_import.html', context)

        if file.size > 5 * 1024 * 1024:
            messages.error(request, 'File size exceeds 5MB limit.')
            return render(request, 'management/student_import.html', context)

        try:
            import openpyxl
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError as DjangoValidationError
            from django.db import transaction

            wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(min_row=2, values_only=True))
            wb.close()

            if not rows:
                messages.error(request, 'The uploaded file contains no data rows.')
                return render(request, 'management/student_import.html', context)

            if len(rows) > 500:
                messages.error(request, 'Maximum 500 rows allowed per import.')
                return render(request, 'management/student_import.html', context)

            # Pre-fetch lookups
            org_batches = {
                b.batch_code.strip().upper(): b
                for b in Batch.objects.filter(organization=org, is_active=True)
            }
            existing_ids = set(
                Student.objects.filter(organization=org).values_list('student_id', flat=True)
            )
            import_ids = set()

            errors = []
            students_data = []

            def clean(val):
                return '' if val is None else str(val).strip()

            def parse_date(val, field_name):
                if val is None or (isinstance(val, str) and val.strip() == ''):
                    return None, None
                if isinstance(val, (date, datetime)):
                    return val if isinstance(val, date) and not isinstance(val, datetime) else val.date() if isinstance(val, datetime) else val, None
                val_str = str(val).strip()
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
                    try:
                        return datetime.strptime(val_str, fmt).date(), None
                    except ValueError:
                        continue
                return None, f'{field_name}: could not parse date "{val_str}". Use YYYY-MM-DD format.'

            gender_map = {'m': 'M', 'male': 'M', 'f': 'F', 'female': 'F', 'o': 'O', 'other': 'O'}

            for idx, row in enumerate(rows):
                row_num = idx + 2
                row_errors = []

                if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                    continue

                row = list(row) + [None] * max(0, 13 - len(row))

                student_id = clean(row[0])
                first_name = clean(row[1])
                last_name = clean(row[2])
                email = clean(row[3])
                phone = clean(row[4])
                gender_raw = clean(row[5])
                dob_raw = row[6]
                address = clean(row[7])
                city = clean(row[8])
                state = clean(row[9])
                pin_code = clean(row[10])
                enrollment_raw = row[11]
                batches_raw = clean(row[12])

                # Required fields
                if not first_name:
                    row_errors.append('First Name is required.')
                if not last_name:
                    row_errors.append('Last Name is required.')
                if not phone:
                    row_errors.append('Phone is required.')
                if not gender_raw:
                    row_errors.append('Gender is required.')
                if not address:
                    row_errors.append('Address is required.')
                if not enrollment_raw:
                    row_errors.append('Enrollment Date is required.')

                # Student ID uniqueness
                if student_id:
                    if student_id in existing_ids:
                        row_errors.append(f'Student ID "{student_id}" already exists.')
                    elif student_id in import_ids:
                        row_errors.append(f'Student ID "{student_id}" is duplicated in this file.')
                    else:
                        import_ids.add(student_id)

                # Phone validation
                if phone and not re.match(r'^[\d\s\-\+\(\)]{7,20}$', phone):
                    row_errors.append('Phone: invalid format (7-20 chars, digits/spaces/+-() allowed).')

                # Gender
                gender = gender_map.get(gender_raw.lower()) if gender_raw else None
                if gender_raw and not gender:
                    row_errors.append(f'Gender "{gender_raw}" is invalid. Use M/Male, F/Female, or O/Other.')

                # Dates
                dob, dob_err = parse_date(dob_raw, 'Date of Birth')
                if dob_err:
                    row_errors.append(dob_err)
                elif dob:
                    if dob > date.today():
                        row_errors.append('Date of Birth cannot be in the future.')
                    if dob.year < 1900:
                        row_errors.append('Date of Birth is not valid (before 1900).')

                enrollment_date, enroll_err = parse_date(enrollment_raw, 'Enrollment Date')
                if enroll_err:
                    row_errors.append(enroll_err)
                elif enrollment_date:
                    if enrollment_date > date.today():
                        row_errors.append('Enrollment Date cannot be in the future.')

                if dob and enrollment_date and enrollment_date < dob:
                    row_errors.append('Enrollment Date cannot be before Date of Birth.')

                # Email
                if email:
                    try:
                        validate_email(email)
                    except DjangoValidationError:
                        row_errors.append(f'Email "{email}" is not valid.')

                # Batches
                batch_objects = []
                if batches_raw:
                    for bc in [b.strip().upper() for b in batches_raw.split(',') if b.strip()]:
                        batch_obj = org_batches.get(bc)
                        if not batch_obj:
                            row_errors.append(f'Batch "{bc}" not found or not active.')
                        else:
                            batch_objects.append(batch_obj)

                if row_errors:
                    errors.append({'row': row_num, 'errors': row_errors})
                else:
                    students_data.append({
                        'student_id': student_id or '',
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'phone': phone,
                        'gender': gender,
                        'date_of_birth': dob,
                        'address': address,
                        'city': city,
                        'state': state,
                        'pin_code': pin_code,
                        'enrollment_date': enrollment_date,
                        'batch_objects': batch_objects,
                    })

            if errors:
                context['errors'] = errors
                context['has_results'] = True
                messages.error(request, f'Import failed: {len(errors)} row(s) have errors. No students were imported.')
            elif not students_data:
                messages.error(request, 'No valid data rows found in the file.')
            else:
                try:
                    with transaction.atomic():
                        for data in students_data:
                            batch_objs = data.pop('batch_objects')
                            student = Student(organization=org, **data)
                            student.save()
                            if batch_objs:
                                student.batches.set(batch_objs)
                    context['success_count'] = len(students_data)
                    context['has_results'] = True
                    messages.success(request, f'Successfully imported {len(students_data)} student(s)!')
                except Exception as e:
                    logger.error(f'Student import error: {e}')
                    messages.error(request, f'An error occurred during import: {str(e)}')

        except Exception as e:
            logger.error(f'Student import file error: {e}')
            messages.error(request, f'Could not read the file: {str(e)}')

    return render(request, 'management/student_import.html', context)


# ─── Parent Portal Views ────────────────────────────────────────────────────

@login_required(login_url='login')
@parent_required
def parent_dashboard(request):
    """Parent portal: show all students linked to this parent's phone number."""
    from .utils import normalize_phone

    user = request.user
    org = user.organization

    # Find all students whose normalized phone matches the parent's username
    all_students = Student.objects.filter(
        organization=org
    ).prefetch_related('batches__course')

    matched_students = [
        s for s in all_students
        if normalize_phone(s.phone) == user.username
    ]

    students_data = []
    for student in matched_students:
        attendances = Attendance.objects.filter(
            student=student, organization=org
        ).select_related('batch__course').order_by('-date')[:20]

        fee_payments = FeePayment.objects.filter(
            student=student, organization=org
        ).select_related('batch__course').order_by('-payment_date')

        # Attendance breakdown counts
        all_att = student.attendances.all()
        att_total = all_att.count()
        att_present = all_att.filter(status='Present').count()
        att_absent = all_att.filter(status='Absent').count()
        att_late = all_att.filter(status='Late').count()

        # Enrollment duration
        days_enrolled = (date.today() - student.enrollment_date).days if student.enrollment_date else 0

        students_data.append({
            'student': student,
            'attendances': attendances,
            'fee_payments': fee_payments,
            'attendance_percentage': student.get_attendance_percentage(),
            'total_fees': student.get_total_fees(),
            'total_paid': student.get_total_paid(),
            'pending_fees': student.get_pending_fees(),
            'att_present': att_present,
            'att_absent': att_absent,
            'att_late': att_late,
            'att_total': att_total,
            'days_enrolled': days_enrolled,
        })

    # Check if parent is still using the default password (phone number)
    is_default_password = user.check_password(user.username)

    context = {
        'students_data': students_data,
        'student_count': len(students_data),
        'is_default_password': is_default_password,
        'org': org,
    }
    return render(request, 'management/parent_dashboard.html', context)


@login_required(login_url='login')
@parent_required
def parent_change_password(request):
    """Allow parent users to change their password."""
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('parent_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'management/parent_change_password.html', {'form': form})
