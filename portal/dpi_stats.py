"""Riepilogo per dipendente: quando ha ricevuto l'ultima volta ogni DPI e se è troppo presto per ridarlo."""

from datetime import timedelta

from django.utils import timezone

from . import dpi

# Durata indicativa (giorni) prima di poter ridare lo stesso DPI. Modificabile dalla pagina Consegna DPI.
DEFAULT_DAYS = {
    'Guanti anti-taglio': 30,
    'Scarpe di sicurezza': 180,
    'Indumenti ad alta visibilità': 180,
    'Pantaloni': 180,
    'T-shirt': 90,
    'Giacche': 365,
}
ICONS = {
    'Guanti anti-taglio': 'bi-hand-index-thumb',
    'Scarpe di sicurezza': 'bi-person-walking',
    'Indumenti ad alta visibilità': 'bi-cone-striped',
    'Pantaloni': 'bi-person-standing',
    'T-shirt': 'bi-person',
    'Giacche': 'bi-person-badge',
}
TINTS = ['#eaf0ff|#2F6BFF', '#e7f7ef|#15803D', '#fff3e0|#B45309', '#f1ebff|#6D28D9', '#e6f6fa|#0E7490', '#fdecec|#BE2530']


def rules():
    from .models import DpiReplacementRule

    out = dict(DEFAULT_DAYS)
    for r in DpiReplacementRule.objects.all():
        out[r.label] = r.days
    return out


def _when(delivery):
    if delivery.delivered_on:
        return delivery.delivered_on
    ts = delivery.signed_at or delivery.created_at
    return timezone.localtime(ts).date()


def _ago(days):
    if days == 0:
        return 'oggi'
    if days == 1:
        return 'ieri'
    if days < 60:
        return f'{days} giorni fa'
    months = days // 30
    return f'{months} mesi fa' if days < 730 else f'{days // 365} anni fa'


def summary(employee):
    """Una voce per ogni DPI standard (anche mai consegnato) più quelli aggiunti a mano."""
    from .models import DPI_STATUS_PENDING, DPI_STATUS_SIGNED, DpiDelivery

    today = timezone.localdate()
    year_ago = today - timedelta(days=365)
    rule_days = rules()
    signed = list(DpiDelivery.objects.filter(employee=employee, status=DPI_STATUS_SIGNED))
    pending = list(DpiDelivery.objects.filter(employee=employee, status=DPI_STATUS_PENDING))

    by_label = {}
    for d in signed:
        when = _when(d)
        for it in d.items or []:
            label = (it.get('label') or '').strip()
            if not label:
                continue
            key = label.lower()
            e = by_label.setdefault(key, {'label': label, 'history': []})
            e['history'].append({'date': when, 'qty': it.get('qty') or 1, 'text': it.get('text') or label})
    pending_labels = {}
    for d in pending:
        for it in d.items or []:
            pending_labels[(it.get('label') or '').strip().lower()] = _when(d)

    order = [label for _k, label, _q in dpi.STANDARD_ITEMS]
    extra = sorted([e['label'] for k, e in by_label.items() if e['label'] not in order], key=str.lower)
    out = []
    for i, label in enumerate(order + extra):
        e = by_label.get(label.lower(), {'label': label, 'history': []})
        hist = sorted(e['history'], key=lambda h: h['date'], reverse=True)
        days_rule = rule_days.get(label)
        bg, fg = TINTS[i % len(TINTS)].split('|')
        item = {
            'label': label, 'icon': ICONS.get(label, 'bi-box-seam'), 'bg': bg, 'fg': fg,
            'rule': days_rule, 'history': hist[:6], 'count': len(hist),
            'year_pieces': sum(h['qty'] for h in hist if h['date'] >= year_ago),
            'year_times': len([h for h in hist if h['date'] >= year_ago]),
            'pending_since': pending_labels.get(label.lower()),
            'standard': label in order,
        }
        if hist:
            last = hist[0]
            days = (today - last['date']).days
            item.update({'last': last['date'], 'last_qty': last['qty'], 'days': days, 'ago': _ago(days)})
            if days_rule:
                pct = min(100, int(round(100 * days / days_rule))) if days_rule else 100
                ready_on = last['date'] + timedelta(days=days_rule)
                item['pct'] = pct
                if days < days_rule:
                    left = days_rule - days
                    item.update({'state': 'early', 'tone': 'danger' if pct < 50 else 'warn',
                                 'state_label': 'Troppo presto' if pct < 50 else 'Quasi',
                                 'state_detail': f'si può ridare dal {ready_on:%d/%m/%Y} (tra {left} giorn{"o" if left == 1 else "i"})'})
                else:
                    item.update({'state': 'ok', 'tone': 'ok', 'state_label': 'Si può ridare',
                                 'state_detail': f'sono passati più di {days_rule} giorni'})
            else:
                item.update({'state': 'info', 'tone': 'muted', 'state_label': 'Consegnato', 'state_detail': '', 'pct': None})
        else:
            item.update({'last': None, 'days': None, 'state': 'never', 'tone': 'info', 'state_label': 'Mai consegnato',
                         'state_detail': 'nessuna consegna firmata', 'pct': None})
        out.append(item)
    return out
