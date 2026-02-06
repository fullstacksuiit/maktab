"""
Custom template tags for pagination and URL manipulation.
"""
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Replace URL parameters while preserving existing ones.
    Usage: {% url_replace page=2 %}
    This will update the 'page' parameter while keeping 'q' (search) and others.
    """
    request = context.get('request')
    if request is None:
        return ''

    query = request.GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()


@register.simple_tag(takes_context=True)
def url_without(context, *args):
    """
    Remove specific parameters from URL.
    Usage: {% url_without 'page' 'filter' %}
    """
    request = context.get('request')
    if request is None:
        return ''

    query = request.GET.copy()
    for key in args:
        if key in query:
            del query[key]
    return query.urlencode()
