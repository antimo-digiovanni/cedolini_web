"""Riquadri per la scheda dipendente in amministrazione: ferie spettanti e scadenze."""

from django import template
from django.utils import timezone

register = template.Library()


@register.inclusion_tag('portal/includes/admin_employee_hr_cards.html', takes_context=True)
def employee_hr_cards(context, employee):
    from ..deadlines import describe
    from ..models import EmployeeDeadline
    from ..vacations import summary

    request = context.get('request')
    year = timezone.localdate().year
    deadlines = [{'d': d, 'state': describe(d)} for d in
                 EmployeeDeadline.objects.filter(employee=employee).order_by('done_on', 'due_date')[:50]]
    return {
        'employee': employee,
        'request': request,
        'csrf_token': context.get('csrf_token'),
        'year': year,
        'vacation': summary(employee, year),
        'deadlines': deadlines,
        'kinds': EmployeeDeadline.KIND_CHOICES,
        'ferie_errore': bool(request and request.GET.get('ferie_errore')),
        'scadenza_errore': bool(request and request.GET.get('scadenza_errore')),
    }
