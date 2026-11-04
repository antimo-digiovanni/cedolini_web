"""Dati della dashboard amministrazione «vetro liquido»: ore per mese, chi è in servizio per zona, indicatori."""

from datetime import date, timedelta

from django.utils import timezone

MONTHS = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic']
ZONE_COLORS = ['#2F6BFF', '#38BDF8', '#7C4DDB', '#22C55E', '#F472B6', '#94A3B8']
OUT_COLOR = '#F59E0B'


def _start(s):
    return s.corrected_started_at or s.started_at


def _end(s):
    return s.corrected_ended_at or s.ended_at


def _add_months(d, n):
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def admin_overview():
    from .admin_todo import admin_todo_items
    from .models import (Announcement, DpiDelivery, Employee, EmployeeDeadline, Payslip, PayslipView,
                         VacationRequest, WorkSession)

    today = timezone.localdate()
    now = timezone.now()
    active = Employee.objects.filter(user__is_active=True).count()

    # Ore lavorate per mese (ultimi 12 mesi, marcature complete)
    first = _add_months(today.replace(day=1), -11)
    hours = {}
    for s in (WorkSession.objects.filter(work_date__gte=first, day_type=WorkSession.DAY_TYPE_WORK,
                                         started_at__isnull=False)
              .only('work_date', 'started_at', 'ended_at', 'corrected_started_at', 'corrected_ended_at')):
        a, b = _start(s), _end(s)
        if a and b and b > a:
            key = (s.work_date.year, s.work_date.month)
            hours[key] = hours.get(key, 0) + (b - a).total_seconds() / 3600
    months = []
    for i in range(12):
        d = _add_months(first, i)
        months.append({'label': MONTHS[d.month - 1], 'hours': int(round(hours.get((d.year, d.month), 0)))})

    # Chi è in servizio adesso, per zona
    on_duty = (WorkSession.objects.select_related('start_zone')
               .filter(work_date=today, day_type=WorkSession.DAY_TYPE_WORK, started_at__isnull=False,
                       ended_at__isnull=True, corrected_ended_at__isnull=True))
    by_zone = {}
    people = set()
    for s in on_duty:
        if s.employee_id in people:
            continue
        people.add(s.employee_id)
        name = s.start_zone.name if (s.start_zone_id and s.start_within_zone) else 'Fuori zona'
        by_zone[name] = by_zone.get(name, 0) + 1
    zones = []
    for i, (name, n) in enumerate(sorted(((k, v) for k, v in by_zone.items() if k != 'Fuori zona'),
                                         key=lambda kv: -kv[1])):
        zones.append({'label': name, 'n': n, 'color': ZONE_COLORS[i % len(ZONE_COLORS)]})
    if by_zone.get('Fuori zona'):
        zones.append({'label': 'Fuori zona', 'n': by_zone['Fuori zona'], 'color': OUT_COLOR})
    on_duty_count = len(people)
    circ = 2 * 3.14159265 * 62
    acc = 0
    for z in zones:
        length = circ * z['n'] / on_duty_count
        z['dash'] = f'{max(length - 2, 0.5):.1f} {circ - length + 2:.1f}'
        z['offset'] = f'{-acc:.1f}'
        acc += length

    todo = {t['label']: t['count'] for t in admin_todo_items()}
    docs = next((v for k, v in todo.items() if k.startswith('Documenti')), 0)

    last = Payslip.objects.order_by('-year', '-month').values('year', 'month').first()
    payslip_pct = None
    if last:
        qs = Payslip.objects.filter(year=last['year'], month=last['month'])
        total = qs.count()
        opened = PayslipView.objects.filter(payslip__in=qs).values('payslip').distinct().count()
        payslip_pct = int(round(100 * opened / total)) if total else None

    since = now - timedelta(days=30)
    ann_total = ann_read = 0
    for ann in Announcement.objects.filter(created_at__gte=since):
        ann_total += ann.recipient_employees().count()
        ann_read += ann.reads.count()
    ann_pct = int(round(100 * ann_read / ann_total)) if ann_total else None

    deadlines = EmployeeDeadline.objects.filter(done_on__isnull=True, due_date__lte=today + timedelta(days=30),
                                                employee__user__is_active=True).count()
    yesterday = today - timedelta(days=1)
    missing_exit = (WorkSession.objects.filter(work_date=yesterday, day_type=WorkSession.DAY_TYPE_WORK,
                                               started_at__isnull=False, ended_at__isnull=True,
                                               corrected_ended_at__isnull=True)
                    .values('employee').distinct().count())

    attention = sum(1 for v in (docs, DpiDelivery.objects.filter(status='pending').count(),
                                VacationRequest.objects.filter(status='pending').count(), deadlines, missing_exit) if v)

    def kpi(label, value, sub, color, url, tag='', tone='', suffix=''):
        return {'label': label, 'value': value, 'sub': sub, 'color': color, 'url': url, 'tag': tag, 'tone': tone,
                'suffix': suffix, 'na': value is None}

    from django.urls import reverse
    kpis = [
        kpi('In servizio ora', on_duty_count, f'su {active} dipendenti attivi', '#4ADE80', reverse('admin_timekeeping'), 'live', 'live'),
        kpi('Documenti da verificare', docs, 'carta d’identità e patente', '#F59E0B', reverse('admin_documents') + '?filtro=verificare', 'nuovi' if docs else '', 'warn'),
        kpi('DPI da firmare', DpiDelivery.objects.filter(status='pending').count(), 'inviate ai dipendenti', '#38BDF8', reverse('admin_dpi') + '?stato=pending'),
        kpi('Ferie in attesa', VacationRequest.objects.filter(status='pending').count(), 'richieste da approvare', '#C4B5FD', reverse('admin_vacation_requests')),
        kpi('Cedolini aperti', payslip_pct, (f'{MONTHS[last["month"] - 1]} {last["year"]}' if last else 'nessun cedolino'), '#9CC0FF', reverse('admin_all_payslips'), suffix='%'),
        kpi('Comunicazioni lette', ann_pct, 'ultimi 30 giorni', '#C4B5FD', reverse('admin_announcements'), suffix='%'),
        kpi('Scadenze entro 30 gg', deadlines, 'formazione e visite mediche', '#F87171', reverse('admin_deadlines') + '?filtro=scadenza', 'attenzione' if deadlines else '', 'danger'),
        kpi('Uscite mancanti', missing_exit, 'ieri · da controllare', '#F59E0B', reverse('admin_timekeeping')),
    ]
    return {'months': months, 'zones': zones, 'on_duty': on_duty_count, 'active': active, 'kpis': kpis,
            'attention': attention}
