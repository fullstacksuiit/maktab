def currency_symbol(request):
    if request.user.is_authenticated:
        # Cache org data on request to avoid repeated FK lookups
        if not hasattr(request, '_cached_org_data'):
            org = request.user.organization
            if org:
                pending_apps = 0
                if request.user.role in ('admin', 'manager'):
                    from management.models import AdmissionApplication, LeaveRequest
                    pending_apps = AdmissionApplication.objects.filter(
                        organization=org, status='pending'
                    ).count()
                    pending_leaves = LeaveRequest.objects.filter(
                        organization=org, status='pending'
                    ).count()
                else:
                    pending_leaves = 0
                request._cached_org_data = {
                    'currency_symbol': org.currency_symbol,
                    'org_latitude': org.latitude,
                    'org_longitude': org.longitude,
                    'pending_application_count': pending_apps,
                    'pending_leave_count': pending_leaves,
                }
            else:
                request._cached_org_data = {'currency_symbol': 'Rs.', 'org_latitude': None, 'org_longitude': None, 'pending_application_count': 0, 'pending_leave_count': 0}
        return request._cached_org_data
    return {'currency_symbol': 'Rs.', 'org_latitude': None, 'org_longitude': None, 'pending_application_count': 0, 'pending_leave_count': 0}
