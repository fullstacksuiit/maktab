import re
from datetime import date
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import (User, Organization, Course, Batch, Student, Staff, Attendance, FeePayment,
                     BehaviorNote, AdmissionApplication, Event, LeaveType, LeaveRequest,
                     SalaryComponent, PayrollComponent, Expense)
from .widgets import (
    styled_text_input, styled_email_input, styled_password_input,
    styled_textarea, styled_date_input, styled_number_input,
    styled_select, styled_select_multiple, searchable_select,
    searchable_select_multiple, TAILWIND_INPUT, TAILWIND_SELECT
)
from .indian_cities import STATE_CHOICES, get_city_choices, get_coordinates


class SignUpForm(UserCreationForm):
    """Form for creating a new organization with an admin user."""
    org_name = forms.CharField(
        max_length=255,
        required=True,
        widget=styled_text_input('Organization Name')
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=styled_text_input('Username')
    )
    email = forms.EmailField(
        required=True,
        widget=styled_email_input('Email Address')
    )
    address = forms.CharField(
        required=True,
        widget=styled_textarea('Street / Area', rows=2)
    )
    state = forms.ChoiceField(
        choices=STATE_CHOICES, required=False,
        widget=forms.Select(attrs={'class': TAILWIND_SELECT, 'id': 'id_state'})
    )
    city = forms.ChoiceField(
        choices=[('', 'Select City')], required=False,
        widget=forms.Select(attrs={'class': TAILWIND_SELECT, 'id': 'id_city'})
    )
    pin_code = forms.CharField(
        max_length=10, required=False,
        widget=styled_text_input('Pin Code')
    )
    contact = forms.CharField(
        max_length=20,
        required=True,
        widget=styled_text_input('Contact Number')
    )
    license = forms.CharField(
        max_length=100,
        required=False,
        widget=styled_text_input('License (Optional)')
    )
    password1 = forms.CharField(
        widget=styled_password_input('Password')
    )
    password2 = forms.CharField(
        widget=styled_password_input('Confirm Password')
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate city choices if state was submitted
        if self.data.get('state'):
            self.fields['city'].choices = get_city_choices(self.data['state'])

    def clean_city(self):
        """Allow any city value submitted (from dynamic dropdown)."""
        return self.cleaned_data.get('city', '')

    def clean_contact(self):
        """Validate contact number format."""
        contact = self.cleaned_data.get('contact')
        if contact and not re.match(r'^[\d\s\-\+\(\)]{7,20}$', contact):
            raise forms.ValidationError('Please enter a valid contact number (7-20 digits).')
        return contact

    def save(self, commit=True):
        """Create organization and admin user."""
        user = super().save(commit=False)
        state = self.cleaned_data.get('state', '')
        city = self.cleaned_data.get('city', '')
        coords = get_coordinates(state, city)
        # Create organization first
        organization = Organization.objects.create(
            org_name=self.cleaned_data['org_name'],
            address=self.cleaned_data['address'],
            city=city,
            state=state,
            pin_code=self.cleaned_data.get('pin_code', ''),
            latitude=coords[0] if coords else None,
            longitude=coords[1] if coords else None,
            contact=self.cleaned_data['contact'],
            license=self.cleaned_data.get('license', ''),
        )
        # Set user as admin of this organization
        user.organization = organization
        user.role = 'admin'
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=styled_text_input('Username', with_icon=True)
    )
    password = forms.CharField(
        widget=styled_password_input('Password', with_icon=True)
    )


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_name', 'course_code', 'description', 'duration_value', 'duration_unit', 'fees', 'fee_period']
        widgets = {
            'course_name': styled_text_input('Enter course name'),
            'course_code': styled_text_input('Auto-generated if left blank'),
            'description': styled_textarea('Enter course description', rows=4),
            'duration_value': styled_number_input('e.g., 6', step='1', min_val=1),
            'duration_unit': styled_select(),
            'fees': styled_number_input('Enter course fees', step='0.01', min_val=0),
            'fee_period': styled_select(),
        }

    def clean_fees(self):
        """Ensure fees are positive."""
        fees = self.cleaned_data.get('fees')
        if fees is not None and fees < 0:
            raise forms.ValidationError('Fees cannot be negative.')
        return fees


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['batch_name', 'batch_code', 'course', 'teachers', 'start_time', 'end_time', 'days', 'max_capacity', 'is_active']
        widgets = {
            'batch_name': styled_text_input('e.g., Morning Batch, Weekend Batch'),
            'batch_code': styled_text_input('Auto-generated if left blank'),
            'course': searchable_select('Search course...'),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': TAILWIND_INPUT}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': TAILWIND_INPUT}),
            'days': styled_select(),
            'max_capacity': styled_number_input('Optional max students', min_val=1),
            'teachers': searchable_select_multiple('Search teachers...'),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-primary focus:ring-primary border-gray-300 rounded'}),
        }


class StudentForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        required=False,
        widget=styled_date_input(max_date=date.today())
    )
    enrollment_date = forms.DateField(
        widget=styled_date_input(max_date=date.today())
    )

    class Meta:
        model = Student
        fields = ['student_id', 'full_name', 'email', 'phone',
                  'date_of_birth', 'gender', 'address', 'city', 'state', 'pin_code',
                  'is_orphan', 'guardian_name', 'guardian_phone',
                  'batches', 'enrollment_date']
        widgets = {
            'student_id': styled_text_input('Auto-generated if left blank'),
            'full_name': styled_text_input('Enter full name'),
            'email': styled_email_input('Enter email address (optional)'),
            'phone': styled_text_input('Enter phone number'),
            'gender': styled_select(),
            'address': styled_textarea('Street / Area', rows=2),
            'city': styled_text_input('City'),
            'state': styled_text_input('State'),
            'pin_code': styled_text_input('Pin Code'),
            'is_orphan': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-primary border-gray-300 rounded focus:ring-primary/50 cursor-pointer'}),
            'guardian_name': styled_text_input('Guardian full name'),
            'guardian_phone': styled_text_input('Guardian phone number'),
            'batches': searchable_select_multiple('Search batches...'),
        }

    def clean_date_of_birth(self):
        """Validate date of birth is not in the future."""
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > date.today():
            raise forms.ValidationError('Date of birth cannot be in the future.')
        if dob and dob < date(1900, 1, 1):
            raise forms.ValidationError('Please enter a valid date of birth.')
        return dob

    def clean_enrollment_date(self):
        """Validate enrollment date is not in the future."""
        enrollment = self.cleaned_data.get('enrollment_date')
        if enrollment and enrollment > date.today():
            raise forms.ValidationError('Enrollment date cannot be in the future.')
        return enrollment

    def clean_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone')
        if phone and not re.match(r'^[\d\s\-\+\(\)]{7,20}$', phone):
            raise forms.ValidationError('Please enter a valid phone number (7-20 digits).')
        return phone

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        dob = cleaned_data.get('date_of_birth')
        enrollment = cleaned_data.get('enrollment_date')

        if dob and enrollment and enrollment < dob:
            self.add_error('enrollment_date', 'Enrollment date cannot be before date of birth.')

        return cleaned_data


class StaffForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=styled_date_input(max_date=date.today())
    )
    joining_date = forms.DateField(
        widget=styled_date_input(max_date=date.today())
    )

    class Meta:
        model = Staff
        fields = ['staff_id', 'first_name', 'last_name', 'email', 'phone',
                  'date_of_birth', 'gender', 'address', 'city', 'state', 'pin_code',
                  'staff_role', 'department', 'joining_date', 'salary', 'working_hours_per_day']
        widgets = {
            'staff_id': styled_text_input('Enter staff ID (e.g., STF001)'),
            'first_name': styled_text_input('Enter first name'),
            'last_name': styled_text_input('Enter last name'),
            'email': styled_email_input('Enter email address (optional)'),
            'phone': styled_text_input('Enter phone number'),
            'gender': styled_select(),
            'address': styled_textarea('Street / Area', rows=2),
            'city': styled_text_input('City'),
            'state': styled_text_input('State'),
            'pin_code': styled_text_input('Pin Code'),
            'staff_role': styled_select(),
            'department': styled_text_input('Enter department'),
            'salary': styled_number_input('Enter monthly salary', step='0.01', min_val=0),
            'working_hours_per_day': styled_number_input('e.g., 8', step='0.5', min_val=0.5),
        }

    def clean_date_of_birth(self):
        """Validate date of birth is not in the future."""
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > date.today():
            raise forms.ValidationError('Date of birth cannot be in the future.')
        if dob and dob < date(1900, 1, 1):
            raise forms.ValidationError('Please enter a valid date of birth.')
        return dob

    def clean_joining_date(self):
        """Validate joining date is not in the future."""
        joining = self.cleaned_data.get('joining_date')
        if joining and joining > date.today():
            raise forms.ValidationError('Joining date cannot be in the future.')
        return joining

    def clean_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone')
        if phone and not re.match(r'^[\d\s\-\+\(\)]{7,20}$', phone):
            raise forms.ValidationError('Please enter a valid phone number (7-20 digits).')
        return phone

    def clean_salary(self):
        """Ensure salary is not negative."""
        salary = self.cleaned_data.get('salary')
        if salary is not None and salary < 0:
            raise forms.ValidationError('Salary cannot be negative.')
        return salary

    def clean_working_hours_per_day(self):
        """Ensure working hours is between 0.5 and 24."""
        hours = self.cleaned_data.get('working_hours_per_day')
        if hours is not None:
            if hours < 0.5:
                raise forms.ValidationError('Working hours must be at least 0.5.')
            if hours > 24:
                raise forms.ValidationError('Working hours cannot exceed 24.')
        return hours

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        dob = cleaned_data.get('date_of_birth')
        joining = cleaned_data.get('joining_date')

        if dob and joining and joining < dob:
            self.add_error('joining_date', 'Joining date cannot be before date of birth.')

        return cleaned_data


class AttendanceFilterForm(forms.Form):
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.none(),
        widget=searchable_select('Search batch...'),
        required=True
    )
    date = forms.DateField(
        widget=styled_date_input(),
        required=True,
        initial=date.today
    )


class StaffAttendanceFilterForm(forms.Form):
    date = forms.DateField(
        widget=styled_date_input(),
        required=True,
        initial=date.today
    )


class SettingsForm(forms.ModelForm):
    """Form for editing organization settings (admin only)."""
    state = forms.ChoiceField(
        choices=STATE_CHOICES, required=False,
        widget=forms.Select(attrs={'class': TAILWIND_SELECT, 'id': 'id_state'})
    )
    city = forms.ChoiceField(
        choices=[('', 'Select City')], required=False,
        widget=forms.Select(attrs={'class': TAILWIND_SELECT, 'id': 'id_city'})
    )

    class Meta:
        model = Organization
        fields = ['org_name', 'contact', 'address', 'state', 'city', 'pin_code',
                  'currency_symbol',
                  'bank_name', 'account_number', 'ifsc_code', 'account_holder', 'upi_id']
        widgets = {
            'org_name': styled_text_input('Organization Name'),
            'contact': styled_text_input('Contact Number'),
            'address': styled_textarea('Street / Area', rows=2),
            'pin_code': styled_text_input('Pin Code'),
            'currency_symbol': styled_text_input('e.g., Rs., $, ₹, €'),
            'bank_name': styled_text_input('e.g., State Bank of India'),
            'account_number': styled_text_input('Enter account number'),
            'ifsc_code': styled_text_input('e.g., SBIN0001234'),
            'account_holder': styled_text_input('Account holder name'),
            'upi_id': styled_text_input('e.g., yourname@upi'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate city choices from existing instance or submitted data
        state = self.data.get('state') if self.data else (self.instance.state if self.instance else None)
        if state:
            self.fields['city'].choices = get_city_choices(state)

    def clean_city(self):
        """Allow any city value submitted (from dynamic dropdown)."""
        return self.cleaned_data.get('city', '')

    def clean_contact(self):
        """Validate contact number format."""
        contact = self.cleaned_data.get('contact')
        if contact and not re.match(r'^[\d\s\-\+\(\)]{7,20}$', contact):
            raise forms.ValidationError('Please enter a valid contact number (7-20 digits).')
        return contact

    def save(self, commit=True):
        org = super().save(commit=False)
        coords = get_coordinates(org.state, org.city)
        org.latitude = coords[0] if coords else None
        org.longitude = coords[1] if coords else None
        if commit:
            org.save()
        return org


class FeePaymentForm(forms.ModelForm):
    payment_date = forms.DateField(
        widget=styled_date_input(max_date=date.today()),
        initial=date.today
    )

    class Meta:
        model = FeePayment
        fields = ['student', 'batch', 'amount', 'payment_date', 'payment_method', 'notes']
        widgets = {
            'student': searchable_select('Search student...'),
            'batch': searchable_select('Search batch...'),
            'amount': styled_number_input('Enter amount', step='0.01', min_val=0.01),
            'payment_method': styled_select(),
            'notes': styled_textarea('Optional notes', rows=3),
        }

    def clean_payment_date(self):
        """Validate payment date is not in the future."""
        payment_date = self.cleaned_data.get('payment_date')
        if payment_date and payment_date > date.today():
            raise forms.ValidationError('Payment date cannot be in the future.')
        return payment_date

    def clean_amount(self):
        """Ensure amount is positive."""
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount


class InviteUserForm(forms.ModelForm):
    """Form for inviting a new user to the organization."""
    password1 = forms.CharField(
        label='Password',
        widget=styled_password_input('Password')
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=styled_password_input('Confirm Password')
    )
    link_staff = forms.ModelChoiceField(
        queryset=Staff.objects.none(),
        required=False,
        widget=searchable_select('Link to existing staff profile (optional)'),
        label='Link Staff Profile'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role']
        widgets = {
            'username': styled_text_input('Username'),
            'email': styled_email_input('Email Address'),
            'first_name': styled_text_input('First Name'),
            'last_name': styled_text_input('Last Name'),
            'role': styled_select(),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        # Exclude parent from manually assignable roles
        self.fields['role'].choices = [
            c for c in User.ROLE_CHOICES if c[0] != 'parent'
        ]
        if organization:
            # Only show staff members without a linked user account
            self.fields['link_staff'].queryset = Staff.objects.filter(
                organization=organization,
                user_account__isnull=True
            )

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return password2

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.organization = self.organization
        if commit:
            user.save()
            # Link staff profile if selected
            link_staff = self.cleaned_data.get('link_staff')
            if link_staff:
                user.staff_profile = link_staff
                user.save()
        return user


class UserEditForm(forms.ModelForm):
    """Form for editing a user's role and details."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'is_active']
        widgets = {
            'first_name': styled_text_input('First Name'),
            'last_name': styled_text_input('Last Name'),
            'email': styled_email_input('Email Address'),
            'role': styled_select(),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-primary focus:ring-primary border-gray-300 rounded'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude parent from manually assignable roles
        self.fields['role'].choices = [
            c for c in User.ROLE_CHOICES if c[0] != 'parent'
        ]


class BehaviorNoteForm(forms.ModelForm):
    date = forms.DateField(
        widget=styled_date_input(max_date=date.today()),
        initial=date.today
    )

    class Meta:
        model = BehaviorNote
        fields = ['student', 'category', 'title', 'description', 'date']
        widgets = {
            'student': searchable_select('Search student...'),
            'category': styled_select(),
            'title': styled_text_input('e.g. Not completing homework'),
            'description': styled_textarea('Describe the behavior in detail...', rows=4),
        }

    def clean_date(self):
        note_date = self.cleaned_data.get('date')
        if note_date and note_date > date.today():
            raise forms.ValidationError('Date cannot be in the future.')
        return note_date


class UserProfileForm(forms.ModelForm):
    """Form for users to edit their own profile."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': styled_text_input('First Name'),
            'last_name': styled_text_input('Last Name'),
            'email': styled_email_input('Email Address'),
        }


class AdmissionApplicationForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        required=False,
        widget=styled_date_input(max_date=date.today())
    )

    class Meta:
        model = AdmissionApplication
        fields = [
            'first_name', 'last_name', 'phone', 'email',
            'date_of_birth', 'gender', 'address', 'city', 'state', 'pin_code',
            'notes',
        ]
        widgets = {
            'first_name': styled_text_input('Enter first name'),
            'last_name': styled_text_input('Enter last name'),
            'phone': styled_text_input('Enter phone number'),
            'email': styled_email_input('Enter email address (optional)'),
            'gender': styled_select(),
            'address': styled_textarea('Street / Area', rows=2),
            'city': styled_text_input('City'),
            'state': styled_text_input('State'),
            'pin_code': styled_text_input('Pin Code'),
            'notes': styled_textarea('Any message or notes for the institute (optional)', rows=3),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and not re.match(r'^[\d\s\-\+\(\)]{7,20}$', phone):
            raise forms.ValidationError('Please enter a valid phone number (7-20 digits).')
        return phone

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > date.today():
            raise forms.ValidationError('Date of birth cannot be in the future.')
        if dob and dob < date(1900, 1, 1):
            raise forms.ValidationError('Please enter a valid date of birth.')
        return dob


class ApplicationRejectForm(forms.Form):
    rejection_reason = forms.CharField(
        required=False,
        widget=styled_textarea('Reason for rejection (optional)', rows=3),
    )


class EventForm(forms.ModelForm):
    start_date = forms.DateField(
        widget=styled_date_input(),
        label='Start Date'
    )
    end_date = forms.DateField(
        required=False,
        widget=styled_date_input(),
        label='End Date'
    )

    class Meta:
        model = Event
        fields = ['title', 'event_type', 'start_date', 'end_date', 'description']
        widgets = {
            'title': styled_text_input('e.g., Eid Holiday, Final Exam'),
            'event_type': styled_select(),
            'description': styled_textarea('Optional details about this event', rows=3),
        }

    def clean_end_date(self):
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')
        if not end_date and start_date:
            return start_date
        return end_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be before start date.')
        return cleaned_data


class LeaveRequestForm(forms.ModelForm):
    start_date = forms.DateField(widget=styled_date_input())
    end_date = forms.DateField(required=False, widget=styled_date_input())

    class Meta:
        model = LeaveRequest
        fields = ['staff', 'leave_type', 'start_date', 'end_date', 'half_day', 'reason']
        widgets = {
            'staff': searchable_select('Select staff member...'),
            'leave_type': styled_select(),
            'half_day': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-primary border-gray-300 rounded focus:ring-primary/50 cursor-pointer'}),
            'reason': styled_textarea('Reason for leave', rows=3),
        }

    def __init__(self, *args, organization=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.user = user
        if organization:
            self.fields['staff'].queryset = Staff.objects.filter(organization=organization)
            self.fields['leave_type'].queryset = LeaveType.objects.filter(organization=organization)

        # If the user is a staff member (not admin/manager), hide the staff field
        if user and user.role == 'staff' and user.staff_profile:
            self.fields['staff'].initial = user.staff_profile
            self.fields['staff'].widget = forms.HiddenInput()

    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        start_date = self.cleaned_data.get('start_date')
        half_day = self.data.get('half_day')
        if half_day and start_date:
            return start_date
        if not end_date and start_date:
            return start_date
        return end_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        half_day = cleaned_data.get('half_day')
        staff = cleaned_data.get('staff')
        leave_type = cleaned_data.get('leave_type')

        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be before start date.')
            return cleaned_data

        if start_date and end_date and staff and leave_type:
            # Calculate days
            if half_day:
                cleaned_data['end_date'] = start_date
                days = 0.5
            else:
                days = (end_date - start_date).days + 1
            cleaned_data['_days'] = days

            # Check balance (skip for unpaid leave with 0 quota)
            if leave_type.days_per_year > 0:
                from .models import LeaveBalance
                balance = LeaveBalance.objects.filter(
                    organization=self.organization, staff=staff,
                    leave_type=leave_type, year=start_date.year
                ).first()
                if balance and balance.remaining < days:
                    self.add_error('leave_type',
                        f'Insufficient balance. {leave_type.name}: {balance.remaining} days remaining, requesting {days} days.')

            # Check overlapping approved leaves
            overlapping = LeaveRequest.objects.filter(
                staff=staff, status__in=['pending', 'approved'],
                start_date__lte=end_date, end_date__gte=start_date
            )
            if self.instance and self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                self.add_error('start_date', 'There is an overlapping leave request for these dates.')

        return cleaned_data


class LeaveRejectForm(forms.Form):
    rejection_reason = forms.CharField(
        required=False,
        widget=styled_textarea('Reason for rejection (optional)', rows=3),
    )


class SalaryComponentForm(forms.ModelForm):
    class Meta:
        model = SalaryComponent
        fields = ['name', 'code', 'component_type', 'is_percentage', 'default_amount', 'description', 'is_active']
        widgets = {
            'name': styled_text_input('Component Name'),
            'code': styled_text_input('Code (e.g., HRA, PF)'),
            'component_type': styled_select(),
            'is_percentage': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-primary border-gray-300 rounded focus:ring-primary'}),
            'default_amount': styled_number_input('Amount or Percentage', step='0.01', min_val=0),
            'description': styled_text_input('Optional description'),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-primary border-gray-300 rounded focus:ring-primary'}),
        }


class PayrollComponentForm(forms.ModelForm):
    class Meta:
        model = PayrollComponent
        fields = ['salary_component', 'name', 'component_type', 'amount', 'notes']
        widgets = {
            'salary_component': styled_select(),
            'name': styled_text_input('Component Name'),
            'component_type': styled_select(),
            'amount': styled_number_input('Amount', step='0.01', min_val=0),
            'notes': styled_text_input('Notes (optional)'),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['salary_component'].queryset = SalaryComponent.objects.filter(
                organization=organization, is_active=True
            )
        self.fields['salary_component'].required = False


class ExpenseForm(forms.ModelForm):
    expense_date = forms.DateField(
        widget=styled_date_input(max_date=date.today()),
        initial=date.today
    )

    class Meta:
        model = Expense
        fields = ['title', 'category', 'amount', 'expense_date', 'payment_method', 'reference_number', 'description']
        widgets = {
            'title': styled_text_input('e.g. Monthly Rent, Electricity Bill'),
            'category': styled_select(),
            'amount': styled_number_input('Enter amount', step='0.01', min_val=0.01),
            'payment_method': styled_select(),
            'reference_number': styled_text_input('Transaction / Reference ID (optional)'),
            'description': styled_textarea('Optional notes', rows=3),
        }

    def clean_expense_date(self):
        expense_date = self.cleaned_data.get('expense_date')
        if expense_date and expense_date > date.today():
            raise forms.ValidationError('Expense date cannot be in the future.')
        return expense_date

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount
