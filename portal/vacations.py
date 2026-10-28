"""Ferie: riepilogo giorni spettanti/usati e dati per il calendario della richiesta."""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST


def _days_in_year(req, year):
    """Giorni (di calendario, inclusi gli estremi: come nel resto del portale) della richiesta che cadono nell'anno."""
    start = max(req.start_date, date(year, 1, 1))
    end = min(req.end_date, date(year, 12, 31))
    return (end - start).days + 1 if end >= start else 0


def summary(employee, year=None):
    """None se l'amministrazione non ha inserito i giorni spettanti per l'anno."""
    from .models import VacationAllowance, VacationRequest

    year = year or timezone.localdate().year
    allowance = VacationAllowance.objects.filter(employee=employee, year=year).first()
    if allowance is None:
        return None
    reqs = VacationRequest.objects.filter(employee=employee, start_date__lte=date(year, 12, 31),
                                          end_date__gte=date(year, 1, 1))
    approved = sum(_days_in_year(r, year) for r in reqs if r.status == VacationRequest.STATUS_APPROVED)
    pending = sum(_days_in_year(r, year) for r in reqs if r.status == VacationRequest.STATUS_PENDING)
    total = allowance.days
    left = total - approved

    def fmt(value):
        value = Decimal(value)
        return f'{value:.1f}'.rstrip('0').rstrip('.').replace('.', ',')

    return {'year': year, 'total': fmt(total), 'approved': fmt(approved), 'pending': fmt(pending),
            'left': fmt(left), 'left_negative': left < 0, 'allowance': allowance}


def calendar_data(employee):
    """Dati per il calendario: giorni bloccati e richieste in attesa/approvate (da un mese fa in poi)."""
    from .models import VacationRequest
    from .views import VACATION_BLOCKED_DAYS

    since = timezone.localdate() - timedelta(days=31)
    reqs = (VacationRequest.objects.filter(employee=employee, end_date__gte=since)
            .exclude(status=VacationRequest.STATUS_REJECTED).order_by('start_date'))
    return {
        'blocked': [[m, d] for m, d in VACATION_BLOCKED_DAYS],
        'requests': [{'start': r.start_date.isoformat(), 'end': r.end_date.isoformat(), 'status': r.status}
                     for r in reqs],
        'today': timezone.localdate().isoformat(),
    }


@login_required
@require_POST
def admin_set_vacation_allowance(request, emp_id):
    from .models import Employee, VacationAllowance
    from .views import _create_audit_event

    if not request.user.is_staff:
        return redirect('dashboard')
    employee = get_object_or_404(Employee, id=emp_id)
    back = reverse('admin_employee_detail', args=[employee.id]) + '#ferie-spettanti'
    try:
        year = int(request.POST.get('year') or timezone.localdate().year)
        raw = (request.POST.get('days') or '').strip().replace(',', '.')
        if raw == '':
            VacationAllowance.objects.filter(employee=employee, year=year).delete()
            return redirect(back)
        days = Decimal(raw)
        if days < 0 or days > 366 or year < 2000 or year > 2100:
            raise InvalidOperation
    except (ValueError, InvalidOperation):
        return redirect(back.replace('#', '?ferie_errore=1#'))
    VacationAllowance.objects.update_or_create(employee=employee, year=year,
                                               defaults={'days': days, 'updated_by': request.user})
    _create_audit_event(request, 'vacation_allowance_set', employee=employee,
                        metadata={'year': year, 'days': str(days)})
    return redirect(back)
