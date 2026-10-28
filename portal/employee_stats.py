"""Statistiche della scheda dipendente in amministrazione."""

from datetime import date, timedelta

from django.utils import timezone

WEEKDAYS = ['L', 'M', 'M', 'G', 'V', 'S', 'D']


def _fmt_hours(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f'{h}h {m:02d}m'


def overview(employee):
    from . import identity_docs, push
    from .announcement_views import visible_announcements
    from .deadlines import open_alerts
    from .models import (DPI_STATUS_PENDING, DPI_STATUS_SIGNED, AnnouncementRead, Cud, CudView, DpiDelivery, Payslip,
                         PayslipView, WorkMarkRequest, WorkSession)
    from .vacations import summary

    today = timezone.localdate()
    month_start = today.replace(day=1)
    year_start = date(today.year, 1, 1)

    sessions = list(WorkSession.objects.filter(employee=employee, work_date__gte=min(month_start, today - timedelta(days=27)),
                                               day_type=WorkSession.DAY_TYPE_WORK, started_at__isnull=False))
    month = [s for s in sessions if s.work_date >= month_start]
    worked_days = len({s.work_date for s in month})
    seconds = sum((s.ended_at - s.started_at).total_seconds() for s in month if s.ended_at and s.ended_at > s.started_at)
    starts = [timezone.localtime(s.started_at) for s in month if s.sequence == 1]
    avg_start = None
    if starts:
        mins = sum(t.hour * 60 + t.minute for t in starts) / len(starts)
        avg_start = f'{int(mins // 60):02d}:{int(mins % 60):02d}'
    missing_exit = len([s for s in month if not s.ended_at and s.work_date < today])

    # Ultimi 28 giorni: ore per giorno (grafico a barre)
    per_day = {}
    for s in sessions:
        if s.ended_at and s.ended_at > s.started_at:
            per_day[s.work_date] = per_day.get(s.work_date, 0) + (s.ended_at - s.started_at).total_seconds()
        else:
            per_day.setdefault(s.work_date, 0)
    days = [today - timedelta(days=i) for i in range(27, -1, -1)]
    max_s = max([per_day.get(d, 0) for d in days] + [8 * 3600])
    chart = []
    for d in days:
        sec = per_day.get(d)
        chart.append({
            'label': WEEKDAYS[d.weekday()], 'date': d,
            'pct': int(round(100 * (sec or 0) / max_s)) if sec else 0,
            'marked': sec is not None, 'weekend': d.weekday() >= 5,
            'title': f'{d:%d/%m}: ' + (_fmt_hours(sec) if sec else ('marcatura senza uscita' if sec == 0 else 'nessuna marcatura')),
        })

    payslips = Payslip.objects.filter(employee=employee)
    payslip_total = payslips.count()
    payslip_opened = PayslipView.objects.filter(payslip__employee=employee).values('payslip').distinct().count()
    cud_total = Cud.objects.filter(employee=employee).count()
    cud_opened = CudView.objects.filter(cud__employee=employee).values('cud').distinct().count()
    last_payslip = payslips.order_by('-year', '-month').first()

    anns = list(visible_announcements(employee).filter(created_at__date__gte=today - timedelta(days=365)))
    ann_read = AnnouncementRead.objects.filter(employee=employee, announcement__in=anns).count()

    dpi_signed = DpiDelivery.objects.filter(employee=employee, status=DPI_STATUS_SIGNED)
    last_dpi = dpi_signed.order_by('-delivered_on', '-id').first()

    out_of_zone = WorkMarkRequest.objects.filter(employee=employee, work_date__gte=year_start).count()

    docs = []
    for kind, doc in identity_docs.latest_by_kind(employee).items():
        docs.append({'label': identity_docs.KIND_LABELS[kind], 'state': identity_docs.describe(doc, kind), 'doc': doc})

    devices = push.describe_user_devices(employee.user)

    def pct(a, b):
        return int(round(100 * a / b)) if b else None

    return {
        'today': today,
        'worked_days': worked_days,
        'hours': _fmt_hours(seconds),
        'avg_start': avg_start,
        'missing_exit': missing_exit,
        'chart': chart,
        'vacation': summary(employee, today.year),
        'payslip_total': payslip_total, 'payslip_opened': payslip_opened,
        'payslip_pct': pct(payslip_opened, payslip_total),
        'cud_total': cud_total, 'cud_opened': cud_opened,
        'last_payslip': last_payslip,
        'ann_total': len(anns), 'ann_read': ann_read, 'ann_pct': pct(ann_read, len(anns)),
        'dpi_count': dpi_signed.count(), 'last_dpi': last_dpi,
        'dpi_pending': DpiDelivery.objects.filter(employee=employee, status=DPI_STATUS_PENDING).count(),
        'out_of_zone': out_of_zone,
        'docs': docs,
        'deadline_alerts': open_alerts(employee),
        'devices': devices,
        'last_login': employee.user.last_login,
        'joined': employee.user.date_joined,
    }
