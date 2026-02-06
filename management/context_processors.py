def currency_symbol(request):
    if request.user.is_authenticated and request.user.organization:
        return {'currency_symbol': request.user.organization.currency_symbol}
    return {'currency_symbol': 'Rs.'}
