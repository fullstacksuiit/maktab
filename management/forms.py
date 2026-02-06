import re
from datetime import date
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Organization, Course, Batch, Student, Staff, Attendance, FeePayment
from .widgets import (
    styled_text_input, styled_email_input, styled_password_input,
    styled_textarea, styled_date_input, styled_number_input,
    styled_select, styled_select_multiple, searchable_select,
    searchable_select_multiple, TAILWIND_INPUT, TAILWIND_SELECT
)


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
        widget=styled_textarea('Address', rows=3)
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

    def clean_contact(self):
        """Validate contact number format."""
        contact = self.cleaned_data.get('contact')
        if contact and not re.match(r'^[\d\s\-\+\(\)]{7,20}$', contact):
            raise forms.ValidationError('Please enter a valid contact number (7-20 digits).')
        return contact

    def save(self, commit=True):
        """Create organization and admin user."""
        user = super().save(commit=False)
        # Create organization first
        organization = Organization.objects.create(
            org_name=self.cleaned_data['org_name'],
            address=self.cleaned_data['address'],
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
        fields = ['course_name', 'course_code', 'description', 'duration', 'fees', 'fee_period']
        widgets = {
            'course_name': styled_text_input('Enter course name'),
            'course_code': styled_text_input('Auto-generated if left blank'),
            'description': styled_textarea('Enter course description', rows=4),
            'duration': styled_text_input('e.g., 6 months, 1 year'),
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
        fields = ['batch_name', 'batch_code', 'course', 'start_time', 'end_time', 'days', 'max_capacity', 'is_active']
        widgets = {
            'batch_name': styled_text_input('e.g., Morning Batch, Weekend Batch'),
            'batch_code': styled_text_input('Auto-generated if left blank'),
            'course': searchable_select('Search course...'),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': TAILWIND_INPUT}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': TAILWIND_INPUT}),
            'days': styled_select(),
            'max_capacity': styled_number_input('Optional max students', min_val=1),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-primary focus:ring-primary border-gray-300 rounded'}),
        }


class StudentForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=styled_date_input(max_date=date.today())
    )
    enrollment_date = forms.DateField(
        widget=styled_date_input(max_date=date.today())
    )

    class Meta:
        model = Student
        fields = ['student_id', 'first_name', 'last_name', 'email', 'phone',
                  'date_of_birth', 'gender', 'address', 'batches', 'enrollment_date']
        widgets = {
            'student_id': styled_text_input('Auto-generated if left blank'),
            'first_name': styled_text_input('Enter first name'),
            'last_name': styled_text_input('Enter last name'),
            'email': styled_email_input('Enter email address'),
            'phone': styled_text_input('Enter phone number'),
            'gender': styled_select(),
            'address': styled_textarea('Enter address', rows=3),
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
                  'date_of_birth', 'gender', 'address', 'staff_role', 'department',
                  'joining_date', 'salary']
        widgets = {
            'staff_id': styled_text_input('Enter staff ID (e.g., STF001)'),
            'first_name': styled_text_input('Enter first name'),
            'last_name': styled_text_input('Enter last name'),
            'email': styled_email_input('Enter email address'),
            'phone': styled_text_input('Enter phone number'),
            'gender': styled_select(),
            'address': styled_textarea('Enter address', rows=3),
            'staff_role': styled_select(),
            'department': styled_text_input('Enter department'),
            'salary': styled_number_input('Enter salary', step='0.01', min_val=0),
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


class SettingsForm(forms.ModelForm):
    """Form for editing organization settings (admin only)."""
    class Meta:
        model = Organization
        fields = ['org_name', 'contact', 'address', 'currency_symbol',
                  'bank_name', 'account_number', 'ifsc_code', 'account_holder', 'upi_id']
        widgets = {
            'org_name': styled_text_input('Organization Name'),
            'contact': styled_text_input('Contact Number'),
            'address': styled_textarea('Address', rows=3),
            'currency_symbol': styled_text_input('e.g., Rs., $, ₹, €'),
            'bank_name': styled_text_input('e.g., State Bank of India'),
            'account_number': styled_text_input('Enter account number'),
            'ifsc_code': styled_text_input('e.g., SBIN0001234'),
            'account_holder': styled_text_input('Account holder name'),
            'upi_id': styled_text_input('e.g., yourname@upi'),
        }

    def clean_contact(self):
        """Validate contact number format."""
        contact = self.cleaned_data.get('contact')
        if contact and not re.match(r'^[\d\s\-\+\(\)]{7,20}$', contact):
            raise forms.ValidationError('Please enter a valid contact number (7-20 digits).')
        return contact


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
