def currency_symbol(request):
    if request.user.is_authenticated:
        # Cache org data on request to avoid repeated FK lookups
        if not hasattr(request, '_cached_org_data'):
            org = request.user.organization
            if org:
                pending_apps = 0
                pending_leaves = 0
                is_punched_in = False

                if request.user.role in ('admin', 'manager'):
                    from management.models import AdmissionApplication, LeaveRequest
                    pending_apps = AdmissionApplication.objects.filter(
                        organization=org, status='pending'
                    ).count()
                    pending_leaves = LeaveRequest.objects.filter(
                        organization=org, status='pending'
                    ).count()
                elif request.user.role == 'staff' and hasattr(request.user, 'staff_profile') and request.user.staff_profile:
                    from management.models import PunchRecord, LeaveRequest
                    from datetime import date
                    # Own pending leaves count
                    pending_leaves = LeaveRequest.objects.filter(
                        organization=org, staff=request.user.staff_profile, status='pending'
                    ).count()
                    # Current punch status
                    last_punch = PunchRecord.objects.filter(
                        staff=request.user.staff_profile, date=date.today(), organization=org
                    ).order_by('timestamp').last()
                    is_punched_in = bool(last_punch and last_punch.punch_type == 'in')

                request._cached_org_data = {
                    'currency_symbol': org.currency_symbol,
                    'org_latitude': org.latitude,
                    'org_longitude': org.longitude,
                    'pending_application_count': pending_apps,
                    'pending_leave_count': pending_leaves,
                    'is_punched_in': is_punched_in,
                }
            else:
                request._cached_org_data = {'currency_symbol': 'Rs.', 'org_latitude': None, 'org_longitude': None, 'pending_application_count': 0, 'pending_leave_count': 0, 'is_punched_in': False}
        return request._cached_org_data
    return {'currency_symbol': 'Rs.', 'org_latitude': None, 'org_longitude': None, 'pending_application_count': 0, 'pending_leave_count': 0, 'is_punched_in': False}
