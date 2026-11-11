"""Restyling «vetro»: riquadro del turno nella home dipendente e tabellone di oggi in dashboard."""

from datetime import timedelta

from django import template
from django.utils import timezone

register = template.Library()

MAX_OPEN_HOURS = 18


def _hours(dt):
    t = timezone.localtime(dt)
    return t.hour + t.minute / 60


def _pct(hours):
    # stringa con il punto: nei template italiani i decimali uscirebbero con la virgola e il CSS non li leggerebbe
    return f'{max(0.0, min(100.0, hours / 24 * 100)):.2f}'


def _fmt_minutes(minutes):
    minutes = max(0, int(minutes))
    return f'{minutes // 60}:{minutes % 60:02d}'


@register.inclusion_tag('portal/includes/glass_shift_card.html')
def shift_card(employee):
    """Stato del turno: in corso (con ore lavorate e zona), concluso oppure da iniziare."""
    from ..models import WorkSession
    now = timezone.now()
    today = timezone.localdate()
    ctx = {'state': 'none', 'employee': employee}
    if employee is None:
        return ctx
    sessions = list(WorkSession.objects.select_related('start_zone')
                    .filter(employee=employee, work_date__gte=today - timedelta(days=1),
                            day_type=WorkSession.DAY_TYPE_WORK)
                    .order_by('work_date', 'sequence'))
    open_s = None
    worked = 0
    first_start = None
    last_end = None
    for s in sessions:
        a, b = s.effective_started_at(), s.effective_ended_at()
        if a and not b and timedelta(0) <= now - a <= timedelta(hours=MAX_OPEN_HOURS):
            open_s = s
        if s.work_date == today or (a and not b and open_s is s):
            if a and b:
                worked += (b - a).total_seconds() / 60
            if a and (first_start is None or a < first_start) and s.work_date == today:
                first_start = a
            if b and (last_end is None or b > last_end):
                last_end = b
    if open_s:
        a = open_s.effective_started_at()
        worked += (now - a).total_seconds() / 60
        start_h = 0 if timezone.localtime(a).date() < today else _hours(a)
        ctx.update(state='open', since=timezone.localtime(a), worked=_fmt_minutes(worked),
                   zone=open_s.start_zone.name if open_s.start_zone_id else '',
                   within=open_s.start_within_zone,
                   band_left=_pct(start_h),
                   band_width=_pct(max(0.6, _hours(now) - start_h)),
                   now_left=_pct(_hours(now)))
    elif last_end and timezone.localtime(last_end).date() == today:
        ctx.update(state='done', worked=_fmt_minutes(worked), until=timezone.localtime(last_end),
                   since=timezone.localtime(first_start) if first_start else None,
                   now_left=_pct(_hours(now)))
    else:
        ctx.update(now_left=_pct(_hours(now)))
    return ctx


@register.inclusion_tag('portal/includes/glass_board.html')
def today_board():
    """Una corsia per zona, una barra per persona: dall'entrata all'uscita (o fino ad adesso)."""
    from ..models import WorkSession
    now = timezone.now()
    today = timezone.localdate()
    now_h = _hours(now)
    rows = (WorkSession.objects.select_related('employee', 'start_zone')
            .filter(work_date__gte=today - timedelta(days=1), day_type=WorkSession.DAY_TYPE_WORK))
    lanes = {}
    counts = {'live': 0, 'done': 0, 'out': 0}
    for s in rows:
        a, b = s.effective_started_at(), s.effective_ended_at()
        if not a:
            continue
        a_day = timezone.localtime(a).date()
        if b and timezone.localtime(b).date() < today:
            continue  # turno di ieri già chiuso
        if not b and now - a > timedelta(hours=MAX_OPEN_HOURS):
            continue  # entrata vecchia senza uscita: la segnala «Marcature da correggere»
        if a_day < today and s.work_date < today and b is None and now - a > timedelta(hours=MAX_OPEN_HOURS):
            continue
        start = 0 if a_day < today else _hours(a)
        end = _hours(b) if b else now_h
        live = b is None
        out = live and not s.start_within_zone
        kind = 'out' if out else ('live' if live else 'done')
        counts['live' if live else 'done'] += 1
        if out:
            counts['out'] += 1
        zone = s.start_zone.name if s.start_zone_id else 'Senza zona'
        emp = s.employee
        label = (emp.last_name or emp.full_name or '').strip()
        if emp.last_name and emp.first_name:
            label = f'{emp.last_name} {emp.first_name[0]}.'
        lanes.setdefault(zone, []).append({'start': start, 'end': max(end, start + 0.25), 'label': label, 'kind': kind,
                                           'title': f'{emp.full_name}: {timezone.localtime(a):%H:%M}'
                                                    + (f' – {timezone.localtime(b):%H:%M}' if b else ' – in servizio')})
    out = []
    for zone, bars in sorted(lanes.items(), key=lambda kv: (-sum(1 for x in kv[1] if x['kind'] != 'done'), kv[0])):
        bars.sort(key=lambda x: (x['start'], x['label']))
        ends = []
        for bar in bars:
            row = next((i for i, e in enumerate(ends) if e + 0.15 <= bar['start']), None)
            if row is None:
                row = len(ends)
                ends.append(0)
            ends[row] = bar['end']
            bar['row'] = row
            bar['left'] = _pct(bar['start'])
            bar['width'] = _pct(bar['end'] - bar['start'])
            bar['top'] = row * 24
        out.append({'zone': zone, 'bars': bars, 'rows': len(ends), 'height': len(ends) * 24,
                    'live': sum(1 for x in bars if x['kind'] != 'done')})
    return {'lanes': out, 'counts': counts, 'now_left': _pct(now_h),
            'now_label': timezone.localtime(now).strftime('%H:%M'),
            'hours': [{'h': f'{h:02d}', 'left': _pct(h)} for h in range(0, 25, 2)]}
