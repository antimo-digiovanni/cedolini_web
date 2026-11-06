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


def _parse_hhmm(raw):
    from datetime import datetime
    try:
        return datetime.strptime((raw or '').strip(), '%H:%M').time()
    except ValueError:
        return None


def correct_session(session, start_t, end_t, user):
    """Imposta gli orari corretti di un turno (entrata e uscita obbligatorie).

    Il giorno si sceglie da solo: fra «ieri, oggi, domani» rispetto al giorno del turno vince quello
    che lascia l'uscita più vicina all'uscita marcata (o l'entrata più vicina all'entrata marcata).
    Un'uscita che non viene dopo l'entrata passa al giorno dopo (turno di notte).
    """
    from datetime import datetime
    tz = timezone.get_current_timezone()
    orig_a, orig_b = session.started_at, session.ended_at

    def same_time(dt, t):
        return dt is not None and timezone.localtime(dt).strftime('%H:%M') == t.strftime('%H:%M')

    # L'orario lasciato uguale a quello marcato fa da riferimento per il giorno.
    if same_time(orig_a, start_t):
        day = timezone.localtime(orig_a).date()
        start_dt = timezone.make_aware(datetime.combine(day, start_t), tz)
        end_dt = timezone.make_aware(datetime.combine(day + timedelta(days=1) if end_t <= start_t else day, end_t), tz)
        return _save_correction(session, start_dt, end_dt, user)
    if same_time(orig_b, end_t):
        day = timezone.localtime(orig_b).date()
        end_dt = timezone.make_aware(datetime.combine(day, end_t), tz)
        start_dt = timezone.make_aware(datetime.combine(day - timedelta(days=1) if start_t >= end_t else day, start_t), tz)
        return _save_correction(session, start_dt, end_dt, user)

    best = None
    for shift in (-1, 0, 1):
        day = session.work_date + timedelta(days=shift)
        start_dt = timezone.make_aware(datetime.combine(day, start_t), tz)
        end_day = day + timedelta(days=1) if end_t <= start_t else day
        end_dt = timezone.make_aware(datetime.combine(end_day, end_t), tz)
        if orig_a:
            score = abs((start_dt - orig_a).total_seconds())
        elif orig_b:
            score = abs((end_dt - orig_b).total_seconds())
        else:
            score = abs(shift)
        if best is None or score < best[0]:
            best = (score, start_dt, end_dt)
    _, start_dt, end_dt = best
    return _save_correction(session, start_dt, end_dt, user)


def _save_correction(session, start_dt, end_dt, user):
    orig_a, orig_b = session.started_at, session.ended_at
    session.day_type = session.DAY_TYPE_WORK
    session.corrected_started_at = start_dt if start_dt != orig_a else None
    session.corrected_ended_at = end_dt if end_dt != orig_b else None
    session.corrected_by = user
    session.corrected_at = timezone.now()
    session.save()
    return start_dt, end_dt


def admin_mark_anomalies(request):
    from django.contrib.auth.views import redirect_to_login
    from django.shortcuts import redirect, render

    from .access import user_has_full_admin_access
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if not user_has_full_admin_access(request.user):
        return redirect('dashboard')
    from django.contrib import messages
    from django.shortcuts import get_object_or_404

    from .models import WorkSession
    from .views import _create_audit_event
    if request.method == 'POST':
        session = get_object_or_404(WorkSession.objects.select_related('employee'), pk=request.POST.get('session_id'))
        start_t, end_t = _parse_hhmm(request.POST.get('start_time')), _parse_hhmm(request.POST.get('end_time'))
        if not start_t or not end_t:
            messages.error(request, f"{session.employee.full_name}: inserisci sia l'entrata sia l'uscita.")
        else:
            start_dt, end_dt = correct_session(session, start_t, end_t, request.user)
            _create_audit_event(request, 'timekeeping_corrected', employee=session.employee, metadata={
                'work_date': str(session.work_date), 'via': 'marcature_da_correggere',
                'corrected_started_at': start_dt.isoformat(), 'corrected_ended_at': end_dt.isoformat(), 'note': None,
            })
            messages.success(request, f"{session.employee.full_name}: turno corretto "
                                      f"{timezone.localtime(start_dt):%d/%m %H:%M} → {timezone.localtime(end_dt):%d/%m %H:%M}.")
        return redirect('admin_mark_anomalies')
    rows = find()
    return render(request, 'portal/admin_mark_anomalies.html', {
        'rows': rows, 'days': DAYS_BACK, 'short_minutes': SHORT_MINUTES, 'long_hours': LONG_HOURS,
    })
