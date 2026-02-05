def currency_symbol(request):
    if request.user.is_authenticated:
        return {'currency_symbol': request.user.currency_symbol}
    return {'currency_symbol': 'Rs.'}
