
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Q, Subquery, OuterRef, DecimalField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from datetime import date
import json

from .forms import (SignUpForm, LoginForm, CourseForm, BatchForm, StudentForm, StaffForm,
                    AttendanceFilterForm, FeePaymentForm, SettingsForm, InviteUserForm, UserEditForm)
from .models import User, Organization, Course, Batch, Student, Staff, Attendance, FeePayment
from .decorators import role_required, admin_required, manager_or_admin_required


def get_org(request):
    """Helper to get the current user's organization."""
    return request.user.organization


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
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
                messages.success(request, f'Assalamu Alaikum, {username}!')
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
def dashboard_view(request):
    org = get_org(request)
    total_courses = Course.objects.filter(organization=org).count()
    total_batches = Batch.objects.filter(organization=org, is_active=True).count()
    total_students = Student.objects.filter(organization=org).count()
    total_staff = Staff.objects.filter(organization=org).count()

    total_revenue = FeePayment.objects.filter(
        organization=org
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Calculate total pending fees based on batches
    total_fees_subquery = Student.objects.filter(
        organization=org
    ).annotate(
        student_total_fees=Coalesce(Sum('batches__course__fees'), 0, output_field=DecimalField())
    ).aggregate(total=Sum('student_total_fees'))['total'] or 0

    total_paid = FeePayment.objects.filter(
        organization=org
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    total_pending = total_fees_subquery - total_paid

    today = date.today()
    today_total = Attendance.objects.filter(organization=org, date=today).count()
    today_present = Attendance.objects.filter(
        organization=org, date=today, status__in=['Present', 'Late']
    ).count()

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
    }
    return render(request, 'management/dashboard_main.html', context)


# ─── Course Views ────────────────────────────────────────────────────────────

@login_required(login_url='login')
def course_list(request):
    org = get_org(request)
    courses_qs = Course.objects.filter(organization=org)

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
def staff_detail(request, pk):
    org = get_org(request)
    staff = get_object_or_404(Staff, pk=pk, organization=org)
    return render(request, 'management/staff_detail.html', {'staff': staff})


# ─── Attendance Views ────────────────────────────────────────────────────────

@login_required(login_url='login')
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
def attendance_mark(request):
    org = get_org(request)
    if request.method == 'POST':
        batch_id = request.POST.get('batch')
        attendance_date = request.POST.get('date')
        batch = get_object_or_404(Batch, pk=batch_id, organization=org)

        students = batch.students.filter(organization=org)
        marked_count = 0
        for student in students:
            status = request.POST.get(f'status_{student.pk}', 'Absent')
            notes = request.POST.get(f'notes_{student.pk}', '')
            Attendance.objects.update_or_create(
                date=attendance_date,
                student=student,
                batch=batch,
                organization=org,
                defaults={
                    'status': status,
                    'marked_by': request.user,
                    'notes': notes,
                }
            )
            marked_count += 1

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
@require_POST
def mark_all_present(request):
    """AJAX endpoint to mark all students present for a batch on a date"""
    org = get_org(request)
    try:
        data = json.loads(request.body)
        batch_id = data.get('batch_id')
        attendance_date = data.get('date')

        batch = get_object_or_404(Batch, pk=batch_id, organization=org)
        students = batch.students.filter(organization=org)

        count = 0
        for student in students:
            Attendance.objects.update_or_create(
                date=attendance_date,
                student=student,
                batch=batch,
                organization=org,
                defaults={
                    'status': 'Present',
                    'marked_by': request.user,
                }
            )
            count += 1

        return JsonResponse({
            'success': True,
            'count': count,
            'message': f'All {count} students marked as Present'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required(login_url='login')
@require_POST
def mark_all_absent(request):
    """AJAX endpoint to mark all students absent for a batch on a date"""
    org = get_org(request)
    try:
        data = json.loads(request.body)
        batch_id = data.get('batch_id')
        attendance_date = data.get('date')

        batch = get_object_or_404(Batch, pk=batch_id, organization=org)
        students = batch.students.filter(organization=org)

        count = 0
        for student in students:
            Attendance.objects.update_or_create(
                date=attendance_date,
                student=student,
                batch=batch,
                organization=org,
                defaults={
                    'status': 'Absent',
                    'marked_by': request.user,
                }
            )
            count += 1

        return JsonResponse({
            'success': True,
            'count': count,
            'message': f'All {count} students marked as Absent'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ─── Fee Payment Views ───────────────────────────────────────────────────────

@login_required(login_url='login')
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
        if form.is_valid():
            form.save()
            messages.success(request, f'Payment #{payment.receipt_number} updated!')
            return redirect('fee_payment_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeePaymentForm(instance=payment)
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
def print_receipt(request, pk):
    org = get_org(request)
    payment = get_object_or_404(FeePayment, pk=pk, organization=org)
    return render(request, 'management/receipt_print.html', {'payment': payment, 'organization': org})


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
