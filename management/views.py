
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from datetime import date

from .forms import (SignUpForm, LoginForm, CourseForm, StudentForm, StaffForm,
                    AttendanceFilterForm, FeePaymentForm, SettingsForm)
from .models import Course, Student, Staff, Attendance, FeePayment


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
    total_courses = Course.objects.filter(created_by=request.user).count()
    total_students = Student.objects.filter(created_by=request.user).count()
    total_staff = Staff.objects.filter(created_by=request.user).count()

    total_revenue = FeePayment.objects.filter(
        created_by=request.user
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    students_qs = Student.objects.filter(created_by=request.user).prefetch_related('courses', 'fee_payments')
    total_pending = sum(s.get_pending_fees() for s in students_qs)

    today = date.today()
    today_total = Attendance.objects.filter(created_by=request.user, date=today).count()
    today_present = Attendance.objects.filter(
        created_by=request.user, date=today, status__in=['Present', 'Late']
    ).count()

    recent_students = Student.objects.filter(created_by=request.user).order_by('-created_at')[:5]
    recent_payments = FeePayment.objects.filter(created_by=request.user).order_by('-created_at')[:5]

    context = {
        'total_courses': total_courses,
        'total_students': total_students,
        'total_staff': total_staff,
        'total_revenue': total_revenue,
        'total_pending': total_pending,
        'today_total': today_total,
        'today_present': today_present,
        'recent_students': recent_students,
        'recent_payments': recent_payments,
    }
    return render(request, 'management/dashboard_main.html', context)


# ─── Course Views ────────────────────────────────────────────────────────────

@login_required(login_url='login')
def course_list(request):
    courses = Course.objects.filter(created_by=request.user)
    return render(request, 'management/course_list.html', {'courses': courses})


@login_required(login_url='login')
def course_add(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.created_by = request.user
            course.save()
            messages.success(request, 'Course added successfully!')
            return redirect('course_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseForm()
    return render(request, 'management/course_form.html', {'form': form, 'action': 'Add'})


@login_required(login_url='login')
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk, created_by=request.user)
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
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, created_by=request.user)
    course.delete()
    messages.success(request, 'Course deleted successfully!')
    return redirect('course_list')


# ─── Student Views ───────────────────────────────────────────────────────────

@login_required(login_url='login')
def student_list(request):
    students = Student.objects.filter(created_by=request.user)
    return render(request, 'management/student_list.html', {'students': students})


@login_required(login_url='login')
def student_add(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.created_by = request.user
            student.save()
            form.save_m2m()
            messages.success(request, 'Student added successfully!')
            return redirect('student_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudentForm()
        form.fields['courses'].queryset = Course.objects.filter(created_by=request.user)
    return render(request, 'management/student_form.html', {'form': form, 'action': 'Add'})


@login_required(login_url='login')
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk, created_by=request.user)
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
        form.fields['courses'].queryset = Course.objects.filter(created_by=request.user)
    return render(request, 'management/student_form.html', {'form': form, 'action': 'Edit'})


@login_required(login_url='login')
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk, created_by=request.user)
    student.delete()
    messages.success(request, 'Student deleted successfully!')
    return redirect('student_list')


@login_required(login_url='login')
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk, created_by=request.user)
    attendances = Attendance.objects.filter(
        student=student, created_by=request.user
    ).order_by('-date')[:20]
    fee_payments = FeePayment.objects.filter(
        student=student, created_by=request.user
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
    student = get_object_or_404(Student, pk=pk, created_by=request.user)
    payments = FeePayment.objects.filter(student=student, created_by=request.user)
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
    staff_members = Staff.objects.filter(created_by=request.user)
    return render(request, 'management/staff_list.html', {'staff_members': staff_members})


@login_required(login_url='login')
def staff_add(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            staff = form.save(commit=False)
            staff.created_by = request.user
            staff.save()
            messages.success(request, 'Staff member added successfully!')
            return redirect('staff_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffForm()
    return render(request, 'management/staff_form.html', {'form': form, 'action': 'Add'})


@login_required(login_url='login')
def staff_edit(request, pk):
    staff = get_object_or_404(Staff, pk=pk, created_by=request.user)
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
def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk, created_by=request.user)
    staff.delete()
    messages.success(request, 'Staff member deleted successfully!')
    return redirect('staff_list')


@login_required(login_url='login')
def staff_detail(request, pk):
    staff = get_object_or_404(Staff, pk=pk, created_by=request.user)
    return render(request, 'management/staff_detail.html', {'staff': staff})


# ─── Attendance Views ────────────────────────────────────────────────────────

@login_required(login_url='login')
def attendance_list(request):
    attendances = Attendance.objects.filter(created_by=request.user).select_related('student', 'course')

    course_id = request.GET.get('course')
    filter_date = request.GET.get('date')
    if course_id:
        attendances = attendances.filter(course_id=course_id)
    if filter_date:
        attendances = attendances.filter(date=filter_date)

    courses = Course.objects.filter(created_by=request.user)

    context = {
        'attendances': attendances[:100],
        'courses': courses,
        'selected_course': course_id,
        'selected_date': filter_date,
    }
    return render(request, 'management/attendance_list.html', context)


@login_required(login_url='login')
def attendance_mark(request):
    if request.method == 'POST':
        course_id = request.POST.get('course')
        attendance_date = request.POST.get('date')
        course = get_object_or_404(Course, pk=course_id, created_by=request.user)

        students = course.students.filter(created_by=request.user)
        marked_count = 0
        for student in students:
            status = request.POST.get(f'status_{student.pk}', 'Absent')
            notes = request.POST.get(f'notes_{student.pk}', '')
            Attendance.objects.update_or_create(
                date=attendance_date,
                student=student,
                course=course,
                created_by=request.user,
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
    form.fields['course'].queryset = Course.objects.filter(created_by=request.user)

    students = None
    selected_course = None
    selected_date = None
    existing_attendance = {}

    if request.GET.get('course') and request.GET.get('date'):
        try:
            selected_course = Course.objects.get(pk=request.GET['course'], created_by=request.user)
            selected_date = request.GET['date']
            students = selected_course.students.filter(created_by=request.user)

            existing = Attendance.objects.filter(
                course=selected_course, date=selected_date, created_by=request.user
            )
            existing_attendance = {a.student_id: a for a in existing}

            form.initial = {'course': selected_course.pk, 'date': selected_date}
        except Course.DoesNotExist:
            pass

    context = {
        'form': form,
        'students': students,
        'selected_course': selected_course,
        'selected_date': selected_date,
        'existing_attendance': existing_attendance,
    }
    return render(request, 'management/attendance_mark.html', context)


# ─── Fee Payment Views ───────────────────────────────────────────────────────

@login_required(login_url='login')
def fee_payment_list(request):
    payments = FeePayment.objects.filter(created_by=request.user).select_related('student', 'course')
    return render(request, 'management/fee_payment_list.html', {'payments': payments})


@login_required(login_url='login')
def fee_payment_add(request):
    if request.method == 'POST':
        form = FeePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.save()
            messages.success(request, f'Payment recorded! Receipt: {payment.receipt_number}')
            return redirect('fee_payment_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeePaymentForm()
        form.fields['student'].queryset = Student.objects.filter(created_by=request.user)
        form.fields['course'].queryset = Course.objects.filter(created_by=request.user)

        student_id = request.GET.get('student')
        if student_id:
            form.initial['student'] = student_id

    return render(request, 'management/fee_payment_add.html', {'form': form, 'action': 'Record'})


# ─── Settings ────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def settings_view(request):
    if request.method == 'POST':
        form = SettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated successfully!')
            return redirect('settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SettingsForm(instance=request.user)
    return render(request, 'management/settings.html', {'form': form})


# ─── Excel Exports ───────────────────────────────────────────────────────────

@login_required(login_url='login')
def export_students_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students"

    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="0D6B4E", end_color="0D6B4E", fill_type="solid")

    headers = ['Student ID', 'First Name', 'Last Name', 'Email', 'Phone',
               'Gender', 'Date of Birth', 'Enrollment Date', 'Enrolled Courses', 'Total Fees']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    students = Student.objects.filter(created_by=request.user)
    for row, student in enumerate(students, 2):
        ws.cell(row=row, column=1, value=student.student_id)
        ws.cell(row=row, column=2, value=student.first_name)
        ws.cell(row=row, column=3, value=student.last_name)
        ws.cell(row=row, column=4, value=student.email)
        ws.cell(row=row, column=5, value=student.phone)
        ws.cell(row=row, column=6, value=student.get_gender_display())
        ws.cell(row=row, column=7, value=str(student.date_of_birth))
        ws.cell(row=row, column=8, value=str(student.enrollment_date))
        ws.cell(row=row, column=9, value=student.get_enrolled_courses_list())
        ws.cell(row=row, column=10, value=float(student.get_total_fees()))

    for col in ws.columns:
        max_length = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 40)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="students.xlsx"'
    wb.save(response)
    return response


@login_required(login_url='login')
def export_staff_excel(request):
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

    staff_members = Staff.objects.filter(created_by=request.user)
    for row, staff in enumerate(staff_members, 2):
        ws.cell(row=row, column=1, value=staff.staff_id)
        ws.cell(row=row, column=2, value=staff.first_name)
        ws.cell(row=row, column=3, value=staff.last_name)
        ws.cell(row=row, column=4, value=staff.email)
        ws.cell(row=row, column=5, value=staff.phone)
        ws.cell(row=row, column=6, value=staff.role)
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
def export_attendance_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance"

    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="0D6B4E", end_color="0D6B4E", fill_type="solid")

    headers = ['Date', 'Student ID', 'Student Name', 'Course', 'Status', 'Notes']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    attendances = Attendance.objects.filter(created_by=request.user).select_related('student', 'course')
    for row, att in enumerate(attendances, 2):
        ws.cell(row=row, column=1, value=str(att.date))
        ws.cell(row=row, column=2, value=att.student.student_id)
        ws.cell(row=row, column=3, value=f"{att.student.first_name} {att.student.last_name}")
        ws.cell(row=row, column=4, value=att.course.course_name)
        ws.cell(row=row, column=5, value=att.status)
        ws.cell(row=row, column=6, value=att.notes or '')

    for col in ws.columns:
        max_length = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 40)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="attendance.xlsx"'
    wb.save(response)
    return response
