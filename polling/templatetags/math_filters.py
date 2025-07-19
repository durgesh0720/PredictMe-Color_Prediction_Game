"""
Custom template filters for mathematical operations
"""
from django import template

register = template.Library()


@register.filter
def mul(value, arg):
    """
    Multiply the value by the argument
    Usage: {{ value|mul:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def div(value, arg):
    """
    Divide the value by the argument
    Usage: {{ value|div:arg }}
    """
    try:
        arg_float = float(arg)
        if arg_float == 0:
            return 0
        return float(value) / arg_float
    except (ValueError, TypeError):
        return 0


@register.filter
def add_float(value, arg):
    """
    Add two numbers and return as float
    Usage: {{ value|add_float:arg }}
    """
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def sub(value, arg):
    """
    Subtract the argument from the value
    Usage: {{ value|sub:arg }}
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calculate percentage of value from total
    Usage: {{ value|percentage:total }}
    """
    try:
        total_float = float(total)
        if total_float == 0:
            return 0
        return (float(value) / total_float) * 100
    except (ValueError, TypeError):
        return 0


@register.filter
def abs_value(value):
    """
    Return absolute value
    Usage: {{ value|abs_value }}
    """
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0


@register.filter
def split(value, delimiter):
    """
    Split string by delimiter
    Usage: {{ value|split:"," }}
    """
    try:
        return str(value).split(str(delimiter))
    except (ValueError, TypeError):
        return []
