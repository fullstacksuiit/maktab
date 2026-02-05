from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm, LoginForm, CourseForm, StudentForm, StaffForm
from .models import Course, Student, Staff

# Create your views here.

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
                messages.success(request, f'Welcome back, {username}!')
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


@login_required(login_url='login')
def dashboard_view(request):
    total_courses = Course.objects.filter(created_by=request.user).count()
    total_students = Student.objects.filter(created_by=request.user).count()
    total_staff = Staff.objects.filter(created_by=request.user).count()

    context = {
        'total_courses': total_courses,
        'total_students': total_students,
        'total_staff': total_staff,
    }
    return render(request, 'management/dashboard_main.html', context)


# Course Views
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


# Student Views
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
            form.save_m2m()  # Save many-to-many relationships
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


# Staff Views
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
