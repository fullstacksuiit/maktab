def currency_symbol(request):
    if request.user.is_authenticated and request.user.organization:
        org = request.user.organization
        return {
            'currency_symbol': org.currency_symbol,
            'org_latitude': org.latitude,
            'org_longitude': org.longitude,
        }
    return {'currency_symbol': 'Rs.', 'org_latitude': None, 'org_longitude': None}
