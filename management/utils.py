import re


def normalize_phone(phone):
    """Strip all non-digit characters from a phone number.
    Returns a digits-only string suitable for use as username/password.
    Strips leading '91' country code if the result is longer than 10 digits.
    """
    if not phone:
        return ''
    digits = re.sub(r'\D', '', phone)
    if len(digits) > 10 and digits.startswith('91'):
        digits = digits[2:]
    return digits
