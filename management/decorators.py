from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*allowed_roles):
    """
    Decorator to restrict view access based on user role.
    Usage: @role_required('admin', 'manager')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in allowed_roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Decorator to restrict view access to admin users only."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin():
            messages.error(request, 'This action requires admin privileges.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_or_admin_required(view_func):
    """Decorator to restrict view access to manager or admin users."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.can_create_edit():
            messages.error(request, 'You do not have permission to perform this action.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def parent_required(view_func):
    """Decorator to restrict view access to parent users only."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_parent():
            messages.error(request, 'This page is for parent/student accounts only.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def internal_user_required(view_func):
    """Decorator to block parent users from accessing internal management views.
    Redirects parent users to their own portal."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_parent():
            return redirect('parent_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_role_required(view_func):
    """Decorator to restrict view access to staff-role users who have a linked staff_profile."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'staff' or not hasattr(request.user, 'staff_profile') or not request.user.staff_profile:
            messages.error(request, 'This page is for staff accounts only.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_user_organization(user):
    """Helper to get user's organization."""
    return user.organization if user.is_authenticated and user.organization else None
