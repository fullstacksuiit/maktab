"""
Reusable form widget factory for consistent Tailwind CSS styling.
Centralizes the styling to avoid repetition across forms.
"""
from django import forms
from datetime import date

# Base CSS classes for form inputs
TAILWIND_INPUT = (
    'w-full px-4 py-2 border border-gray-300 rounded-xl '
    'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-shadow'
)

TAILWIND_INPUT_WITH_ICON = (
    'w-full px-4 py-3 border border-gray-300 rounded-xl '
    'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-shadow pl-10'
)

TAILWIND_SELECT = (
    'w-full px-4 py-2 border border-gray-300 rounded-xl '
    'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary bg-white'
)


def styled_text_input(placeholder='', with_icon=False, **extra_attrs):
    """Create a styled text input widget."""
    css_class = TAILWIND_INPUT_WITH_ICON if with_icon else TAILWIND_INPUT
    attrs = {'class': css_class, 'placeholder': placeholder}
    attrs.update(extra_attrs)
    return forms.TextInput(attrs=attrs)


def styled_email_input(placeholder=''):
    """Create a styled email input widget."""
    return forms.EmailInput(attrs={
        'class': TAILWIND_INPUT,
        'placeholder': placeholder
    })


def styled_password_input(placeholder='', with_icon=False):
    """Create a styled password input widget."""
    css_class = TAILWIND_INPUT_WITH_ICON if with_icon else TAILWIND_INPUT
    return forms.PasswordInput(attrs={
        'class': css_class,
        'placeholder': placeholder
    })


def styled_textarea(placeholder='', rows=3):
    """Create a styled textarea widget."""
    return forms.Textarea(attrs={
        'class': TAILWIND_INPUT,
        'placeholder': placeholder,
        'rows': rows
    })


def styled_date_input(max_date=None):
    """Create a styled date input widget with optional max date."""
    attrs = {
        'class': TAILWIND_INPUT,
        'type': 'date'
    }
    if max_date:
        attrs['max'] = max_date.isoformat() if isinstance(max_date, date) else max_date
    return forms.DateInput(attrs=attrs)


def styled_number_input(placeholder='', step='0.01', min_val=None):
    """Create a styled number input widget."""
    attrs = {
        'class': TAILWIND_INPUT,
        'placeholder': placeholder,
        'step': step
    }
    if min_val is not None:
        attrs['min'] = str(min_val)
    return forms.NumberInput(attrs=attrs)


def styled_select():
    """Create a styled select widget."""
    return forms.Select(attrs={'class': TAILWIND_SELECT})


def styled_select_multiple(size=5):
    """Create a styled multi-select widget."""
    return forms.SelectMultiple(attrs={
        'class': TAILWIND_INPUT,
        'size': str(size)
    })


# Searchable select classes (used with Tom Select)
SEARCHABLE_SELECT = 'searchable-select'
SEARCHABLE_SELECT_MULTIPLE = 'searchable-select-multiple'


def searchable_select(placeholder='Select...'):
    """Create a searchable select widget using Tom Select."""
    return forms.Select(attrs={
        'class': SEARCHABLE_SELECT,
        'data-placeholder': placeholder
    })


def searchable_select_multiple(placeholder='Select...'):
    """Create a searchable multi-select widget using Tom Select."""
    return forms.SelectMultiple(attrs={
        'class': SEARCHABLE_SELECT_MULTIPLE,
        'data-placeholder': placeholder
    })
