"""Riepilogo «Da fare» per la dashboard amministrazione."""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone


def admin_todo_items():
    """Lista di cose in sospeso: [{'label', 'count', 'url', 'icon', 'tone'}], solo quelle con count > 0."""
    from .models import DPI_STATUS_PENDING, Announcement, DpiDelivery, IdentityDocument

    items = []
    # Come il filtro «Da verificare» della pagina documenti: conta solo l'ultimo caricamento per tipo
    # (un caricamento vecchio sostituito da uno nuovo non è più da verificare).
    from .identity_docs import latest_by_kind
    from .models import Employee

    docs = 0
    for emp in Employee.objects.prefetch_related('identity_documents'):
        docs += sum(1 for d in latest_by_kind(emp).values()
                    if d is not None and d.status == IdentityDocument.STATUS_PENDING)
    if docs:
        items.append({'label': 'Documenti da verificare', 'count': docs, 'icon': 'bi-person-vcard', 'tone': 'info',
                      'url': reverse('admin_documents') + '?filtro=verificare'})
    dpi = DpiDelivery.objects.filter(status=DPI_STATUS_PENDING).count()
    if dpi:
        items.append({'label': 'Consegne DPI non ancora firmate', 'count': dpi, 'icon': 'bi-shield-check',
                      'tone': 'warn', 'url': reverse('admin_dpi')})
    since = timezone.now() - timedelta(days=30)
    unread = 0
    for ann in Announcement.objects.filter(created_at__gte=since):
        unread += max(0, ann.recipient_employees().count() - ann.reads.count())
    if unread:
        items.append({'label': 'Letture mancanti delle comunicazioni (ultimi 30 giorni)', 'count': unread,
                      'icon': 'bi-megaphone', 'tone': 'muted', 'url': reverse('admin_announcements')})
    return items
