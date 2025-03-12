from django import template

register = template.Library()

#workaround since django templates doesn't support directly indexing into a tuple / array
@register.filter
def get_note(value):
    return value[0]

@register.filter
def get_file(value):
    return value[1]