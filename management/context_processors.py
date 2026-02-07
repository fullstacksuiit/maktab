def currency_symbol(request):
    if request.user.is_authenticated:
        # Cache org data on request to avoid repeated FK lookups
        if not hasattr(request, '_cached_org_data'):
            org = request.user.organization
            if org:
                request._cached_org_data = {
                    'currency_symbol': org.currency_symbol,
                    'org_latitude': org.latitude,
                    'org_longitude': org.longitude,
                }
            else:
                request._cached_org_data = {'currency_symbol': 'Rs.', 'org_latitude': None, 'org_longitude': None}
        return request._cached_org_data
    return {'currency_symbol': 'Rs.', 'org_latitude': None, 'org_longitude': None}
