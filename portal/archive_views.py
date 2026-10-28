"""Archivio amministrazione: tutti i documenti dei dipendenti in un'unica pagina, con ZIP per dipendente."""

import io
import logging
import os
import zipfile

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import DPI_STATUS_SIGNED, Cud, DpiDelivery, Employee, IdentityDocument, Payslip
from .views import _create_audit_event

logger = logging.getLogger(__name__)

MONTHS = ['', 'gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre',
          'ottobre', 'novembre', 'dicembre']
TYPES = {'': 'Tutti', 'cedolini': 'Cedolini', 'cud': 'CUD', 'dpi': 'Consegne DPI', 'identita': 'Documenti identità'}
LIMIT_PER_TYPE = 600


def collect(employee=None, kind='', year=None):
    """Elenco unico dei documenti: dict con data, tipo, titolo, stato, link."""
    items = []
    emp_filter = {'employee': employee} if employee else {}
    if kind in ('', 'cedolini'):
        qs = Payslip.objects.select_related('employee').prefetch_related('payslipview_set').filter(**emp_filter)
        if year:
            qs = qs.filter(year=year)
        for p in qs.order_by('-uploaded_at')[:LIMIT_PER_TYPE]:
            opened = bool(p.payslipview_set.all())
            items.append({'when': p.uploaded_at, 'type': 'Cedolino', 'icon': 'bi-file-earmark-text', 'tone': 'info',
                          'title': f'{MONTHS[p.month].capitalize() if 0 < p.month < 13 else p.month} {p.year}',
                          'employee': p.employee, 'state': 'Aperto' if opened else 'Non aperto',
                          'state_tone': 'ok' if opened else 'warn',
                          'url': reverse('open_payslip', args=[p.id]), 'field': p.pdf,
                          'zipname': f'cedolini/{p.year}-{p.month:02d}.pdf'})
    if kind in ('', 'cud'):
        qs = Cud.objects.select_related('employee').prefetch_related('cudview_set').filter(**emp_filter)
        if year:
            qs = qs.filter(year=year)
        for c in qs.order_by('-uploaded_at')[:LIMIT_PER_TYPE]:
            opened = bool(c.cudview_set.all())
            items.append({'when': c.uploaded_at, 'type': 'CUD', 'icon': 'bi-file-earmark-ruled', 'tone': 'info',
                          'title': f'CUD {c.year}', 'employee': c.employee,
                          'state': 'Aperto' if opened else 'Non aperto', 'state_tone': 'ok' if opened else 'warn',
                          'url': reverse('open_cud', args=[c.id]), 'field': c.pdf, 'zipname': f'cud/CUD-{c.year}.pdf'})
    if kind in ('', 'dpi'):
        qs = DpiDelivery.objects.select_related('employee').filter(status=DPI_STATUS_SIGNED, **emp_filter)
        if year:
            qs = qs.filter(delivered_on__year=year)
        for d in qs.order_by('-signed_at', '-id')[:LIMIT_PER_TYPE]:
            if not d.pdf:
                continue
            items.append({'when': d.signed_at or d.created_at, 'type': 'Consegna DPI', 'icon': 'bi-shield-check',
                          'tone': 'muted', 'title': (d.items_text or 'Consegna DPI')[:80], 'employee': d.employee,
                          'state': 'Firmata', 'state_tone': 'ok', 'url': reverse('open_dpi', args=[d.id]),
                          'field': d.pdf, 'zipname': f'dpi/consegna-{(d.delivered_on or d.created_at.date()):%Y-%m-%d}-{d.id}.pdf'})
    if kind in ('', 'identita'):
        qs = IdentityDocument.objects.select_related('employee').filter(**emp_filter)
        if year:
            qs = qs.filter(uploaded_at__year=year)
        for doc in qs.order_by('-uploaded_at')[:LIMIT_PER_TYPE]:
            tone = {'approved': 'ok', 'pending': 'info', 'rejected': 'danger'}.get(doc.status, 'muted')
            items.append({'when': doc.uploaded_at, 'type': doc.get_kind_display(), 'icon': 'bi-person-vcard',
                          'tone': 'warn', 'title': f'Scadenza {doc.expiry_date:%d/%m/%Y}', 'employee': doc.employee,
                          'state': doc.get_status_display(), 'state_tone': tone,
                          'url': reverse('admin_document_detail', args=[doc.id]), 'doc': doc,
                          'zipname': f'documenti/{doc.kind}-{doc.uploaded_at:%Y-%m-%d}-{doc.id}.pdf'})
    items.sort(key=lambda i: i['when'].timestamp() if i['when'] else 0, reverse=True)
    return items


@login_required
def admin_archive(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    kind = request.GET.get('tipo', '')
    if kind not in TYPES:
        kind = ''
    employees = Employee.objects.select_related('user').order_by('last_name', 'first_name')
    employee = None
    emp_id = request.GET.get('dipendente') or ''
    if emp_id.isdigit():
        employee = employees.filter(id=emp_id).first()
    year = request.GET.get('anno') or ''
    year = int(year) if year.isdigit() else None
    items = collect(employee, kind, year)
    counts = {}
    for it in items:
        counts[it['type']] = counts.get(it['type'], 0) + 1
    page = Paginator(items, 60).get_page(request.GET.get('pagina'))
    years = sorted({p for p in Payslip.objects.values_list('year', flat=True).distinct()}, reverse=True)
    return render(request, 'portal/admin_archive.html', {
        'page': page, 'types': TYPES, 'kind': kind, 'employees': employees, 'employee': employee,
        'year': year, 'years': years, 'total': len(items), 'counts': sorted(counts.items()),
    })


def _read(field):
    field.open('rb')
    try:
        return field.read()
    finally:
        field.close()


@login_required
def admin_archive_zip(request, emp_id):
    """Tutti i documenti di un dipendente in un file ZIP, divisi per cartelle."""
    from . import identity_docs

    if not request.user.is_staff:
        return HttpResponse('Non autorizzato', status=403)
    employee = get_object_or_404(Employee, id=emp_id)
    buf = io.BytesIO()
    count = 0
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for it in collect(employee):
            try:
                if 'doc' in it:
                    data = identity_docs.build_pdf(it['doc'])
                else:
                    data = _read(it['field'])
            except Exception:
                logger.exception('archivio zip: file non leggibile per %s', it.get('zipname'))
                continue
            zf.writestr(it['zipname'], data)
            count += 1
    name = f'documenti-{(employee.last_name or "")}-{(employee.first_name or "")}'.strip('-').replace(' ', '_')
    response = HttpResponse(buf.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{name or "documenti"}.zip"'
    response['Cache-Control'] = 'no-store'
    _create_audit_event(request, 'archive_zip_downloaded', employee=employee, metadata={'count': count})
    return response
