from django import template

from shop.formatting import format_uah

register = template.Library()


@register.filter
def currency(value):
    return format_uah(value)
