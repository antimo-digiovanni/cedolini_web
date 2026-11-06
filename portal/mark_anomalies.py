"""Marcature da sistemare: turni chiusi dopo pochi minuti, uscite o entrate mancanti, turni troppo lunghi.

Mostrate ogni mattina nella dashboard amministrazione, così si correggono giorno per giorno.
Una marcatura corretta dall'ufficio (orari corretti) non compare più se gli orari corretti sono in regola.
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

DAYS_BACK = 7
SHORT_MINUTES = 5
LONG_HOURS = 16


def find(days=DAYS_BACK):
    from .models import WorkMarkRequest, WorkSession
    from .views import MAX_SHIFT_DURATION_HOURS

    now = timezone.now()
    today = timezone.localdate()
    since = today - timedelta(days=days)
    pending = {}
    for r in WorkMarkRequest.objects.filter(status=WorkMarkRequest.STATUS_PENDING, work_date__gte=since - timedelta(days=1)):
        pending.setdefault(r.employee_id, []).append(r)

    out = []
    sessions = (WorkSession.objects.select_related('employee')
                .filter(work_date__gte=since, day_type=WorkSession.DAY_TYPE_WORK)
                .order_by('-work_date', 'employee__last_name', 'employee__first_name', 'sequence'))
    for s in sessions:
        a, b = s.effective_started_at(), s.effective_ended_at()
        if not a and not b:
            continue
        kind = detail = None
        if a and b:
            minutes = (b - a).total_seconds() / 60
            if minutes < SHORT_MINUTES:
                kind, label = 'short', 'Entrata e uscita nello stesso momento'
                detail = f"{timezone.localtime(a):%H:%M} → {timezone.localtime(b):%H:%M}: probabilmente ha dimenticato l'entrata del turno"
            elif minutes > LONG_HOURS * 60:
                kind, label = 'long', 'Turno troppo lungo'
                detail = (f"{timezone.localtime(a):%d/%m %H:%M} → {timezone.localtime(b):%d/%m %H:%M} "
                          f"({int(minutes // 60)} ore): probabilmente ha dimenticato l'uscita")
        elif a and not b:
            if (now - a) > timedelta(hours=MAX_SHIFT_DURATION_HOURS):
                kind, label = 'no_exit', 'Uscita mancante'
                detail = f"entrata alle {timezone.localtime(a):%d/%m %H:%M}, nessuna uscita"
        elif b and not a:
            waiting = any(r.mark_type in (WorkMarkRequest.MARK_TYPE_START, WorkMarkRequest.MARK_TYPE_BOTH)
                          for r in pending.get(s.employee_id, []))
            if not waiting:
                kind, label = 'no_entry', 'Entrata mancante'
                detail = f"uscita alle {timezone.localtime(b):%d/%m %H:%M}, nessuna entrata"
        if not kind:
            continue
        d = s.work_date
        url = (reverse('admin_timekeeping') + f"?employee={s.employee_id}&year={d.year}&month={d.month}")
        out.append({'session': s, 'employee': s.employee, 'date': d, 'kind': kind, 'label': label,
                    'detail': detail, 'url': url})
    return out


def admin_mark_anomalies(request):
    from django.contrib.auth.views import redirect_to_login
    from django.shortcuts import redirect, render

    from .access import user_has_full_admin_access
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if not user_has_full_admin_access(request.user):
        return redirect('dashboard')
    rows = find()
    return render(request, 'portal/admin_mark_anomalies.html', {
        'rows': rows, 'days': DAYS_BACK, 'short_minutes': SHORT_MINUTES, 'long_hours': LONG_HOURS,
    })
