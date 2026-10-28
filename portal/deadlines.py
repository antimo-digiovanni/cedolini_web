"""Scadenze dei dipendenti (formazione, visite mediche, altro): stato, avvisi e pagine admin."""

import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

WARNING_DAYS = 30


def describe(dl, today=None):
    today = today or timezone.localdate()
    if dl.done_on:
        return {'code': 'done', 'tone': 'ok', 'label': 'Fatto', 'detail': f'Fatto il {dl.done_on:%d/%m/%Y}'}
    days = (dl.due_date - today).days
    if days < 0:
        return {'code': 'expired', 'tone': 'danger', 'label': 'Scaduta', 'detail': f'Scaduta il {dl.due_date:%d/%m/%Y}'}
    if days <= WARNING_DAYS:
        when = 'oggi' if days == 0 else ('domani' if days == 1 else f'tra {days} giorni')
        return {'code': 'expiring', 'tone': 'warn', 'label': 'In scadenza',
                'detail': f'Scade il {dl.due_date:%d/%m/%Y} ({when})'}
    return {'code': 'valid', 'tone': 'ok', 'label': 'In regola', 'detail': f'Scade il {dl.due_date:%d/%m/%Y}'}


def open_alerts(employee):
    """Scadenze non ancora fatte che sono scadute o scadono entro 30 giorni."""
    from .models import EmployeeDeadline

    limit = timezone.localdate() + timedelta(days=WARNING_DAYS)
    out = []
    for dl in EmployeeDeadline.objects.filter(employee=employee, done_on__isnull=True, due_date__lte=limit):
        out.append((dl, describe(dl)))
    return out


def run_notifications():
    """Una notifica al dipendente (e un riepilogo agli admin) per ogni scadenza che entra nei 30 giorni."""
    from django.contrib.auth.models import User

    from . import push
    from .models import EmployeeDeadline

    today = timezone.localdate()
    limit = today + timedelta(days=WARNING_DAYS)
    due = list(EmployeeDeadline.objects.select_related('employee__user')
               .filter(done_on__isnull=True, notified_on__isnull=True, due_date__lte=limit))
    for dl in due:
        when = 'è scaduta' if dl.due_date < today else f'scade il {dl.due_date:%d/%m/%Y}'
        try:
            push.send_to_user(dl.employee.user, title=f'{dl.get_kind_display()} in scadenza',
                              body=f'«{dl.title}» {when}. L\'ufficio del personale ti contatterà per organizzarla.',
                              url=reverse('employee_documents') + '#scadenze', tag=f'scadenza-{dl.id}')
        except Exception:
            logger.exception('scadenze: notifica al dipendente non riuscita')
        dl.notified_on = today
        dl.save(update_fields=['notified_on'])
    if due:
        names = ', '.join(sorted({d.employee.full_name for d in due}))[:150]
        for admin in User.objects.filter(is_staff=True, is_active=True, push_subscriptions__isnull=False).distinct():
            try:
                push.send_to_user(admin, title=f'{len(due)} scadenz{"a" if len(due) == 1 else "e"} entro 30 giorni',
                                  body=names, url=reverse('admin_deadlines'), tag='scadenze-admin')
            except Exception:
                logger.exception('scadenze: notifica admin non riuscita')
    return len(due)


# ------------------------------------------------------------------ amministrazione

FILTERS = {'prossime': 'Da fare', 'scadenza': 'Scadute o entro 30 giorni', 'fatte': 'Fatte', 'tutte': 'Tutte'}


@login_required
def admin_deadlines(request):
    from .models import EmployeeDeadline

    if not request.user.is_staff:
        return redirect('dashboard')
    filtro = request.GET.get('filtro', 'prossime')
    if filtro not in FILTERS:
        filtro = 'prossime'
    qs = EmployeeDeadline.objects.select_related('employee').filter(employee__user__is_active=True)
    today = timezone.localdate()
    counts = {
        'prossime': qs.filter(done_on__isnull=True).count(),
        'scadenza': qs.filter(done_on__isnull=True, due_date__lte=today + timedelta(days=WARNING_DAYS)).count(),
        'fatte': qs.filter(done_on__isnull=False).count(),
        'tutte': qs.count(),
    }
    if filtro == 'prossime':
        qs = qs.filter(done_on__isnull=True)
    elif filtro == 'scadenza':
        qs = qs.filter(done_on__isnull=True, due_date__lte=today + timedelta(days=WARNING_DAYS))
    elif filtro == 'fatte':
        qs = qs.filter(done_on__isnull=False).order_by('-done_on')
    rows = [{'d': d, 'state': describe(d, today)} for d in qs[:300]]
    return render(request, 'portal/admin_deadlines.html', {'rows': rows, 'filters': FILTERS, 'filtro': filtro,
                                                           'counts': counts})


@login_required
@require_POST
def admin_add_deadline(request, emp_id):
    from datetime import date

    from .models import Employee, EmployeeDeadline
    from .views import _create_audit_event

    if not request.user.is_staff:
        return redirect('dashboard')
    employee = get_object_or_404(Employee, id=emp_id)
    back = reverse('admin_employee_detail', args=[employee.id])
    title = (request.POST.get('title') or '').strip()[:150]
    kind = request.POST.get('kind')
    if kind not in dict(EmployeeDeadline.KIND_CHOICES):
        kind = EmployeeDeadline.KIND_OTHER
    try:
        due = date.fromisoformat(request.POST.get('due_date') or '')
    except ValueError:
        due = None
    if not title or not due:
        return redirect(back + '?scadenza_errore=1#scadenze')
    dl = EmployeeDeadline.objects.create(employee=employee, kind=kind, title=title, due_date=due,
                                         note=(request.POST.get('note') or '').strip()[:255],
                                         created_by=request.user)
    _create_audit_event(request, 'deadline_added', employee=employee, metadata={'deadline_id': dl.id})
    return redirect(back + '#scadenze')


@login_required
@require_POST
def admin_update_deadline(request, dl_id):
    from datetime import date

    from .models import EmployeeDeadline
    from .views import _create_audit_event

    if not request.user.is_staff:
        return redirect('dashboard')
    dl = get_object_or_404(EmployeeDeadline.objects.select_related('employee'), id=dl_id)
    action = request.POST.get('action')
    if action == 'done':
        dl.done_on = timezone.localdate()
        dl.save(update_fields=['done_on'])
        # Prossima scadenza (es. corso da ripetere): se indicata, viene creata subito.
        try:
            next_due = date.fromisoformat(request.POST.get('next_due') or '')
        except ValueError:
            next_due = None
        if next_due:
            EmployeeDeadline.objects.create(employee=dl.employee, kind=dl.kind, title=dl.title, due_date=next_due,
                                            note=dl.note, created_by=request.user)
    elif action == 'reopen':
        dl.done_on = None
        dl.save(update_fields=['done_on'])
    elif action == 'delete':
        _create_audit_event(request, 'deadline_deleted', employee=dl.employee,
                            metadata={'title': dl.title, 'due_date': dl.due_date.isoformat()})
        dl.delete()
    nxt = request.POST.get('next') or ''
    if nxt.startswith('/'):
        return redirect(nxt)
    return redirect(reverse('admin_employee_detail', args=[dl.employee_id]) + '#scadenze')
