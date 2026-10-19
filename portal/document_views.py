"""Visualizzatore di cedolini e CUD dentro il portale.

Sull'app installata (iPhone) un PDF aperto direttamente occupa tutto lo schermo senza
pulsanti per tornare indietro, scaricare o condividere: qui il documento è mostrato
come immagini dentro una pagina del portale, con i pulsanti sopra.
"""

import logging
import os

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Cud, Payslip
from .views import _disable_response_cache, track_cud_open, track_payslip_open

logger = logging.getLogger(__name__)

MONTHS_IT = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio',
             'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
MAX_PAGES = 20


def _get_document(request, kind, doc_id):
    if kind == 'cedolino':
        doc = get_object_or_404(Payslip.objects.select_related('employee__user'), id=doc_id)
        month = MONTHS_IT[doc.month - 1] if 1 <= doc.month <= 12 else str(doc.month)
        title = f'Cedolino {month} {doc.year}'
        raw_url = reverse('open_payslip', args=[doc.id])
        fallback = f'cedolino-{doc.year}-{doc.month:02d}.pdf'
    elif kind == 'cud':
        doc = get_object_or_404(Cud.objects.select_related('employee__user'), id=doc_id)
        title = f'CUD {doc.year}'
        raw_url = reverse('open_cud', args=[doc.id])
        fallback = f'cud-{doc.year}.pdf'
    else:
        raise Http404
    if not request.user.is_staff and doc.employee.user_id != request.user.id:
        return None, None, None, None
    filename = os.path.basename(doc.pdf.name) or fallback
    return doc, title, raw_url, filename


def _read_pdf(doc):
    doc.pdf.open('rb')
    try:
        return doc.pdf.read()
    finally:
        doc.pdf.close()


@login_required
def view_document(request, kind, doc_id):
    doc, title, raw_url, filename = _get_document(request, kind, doc_id)
    if doc is None:
        return HttpResponse('Non autorizzato', status=403)

    page_count = 1
    try:
        import fitz  # PyMuPDF
        with fitz.open(stream=_read_pdf(doc), filetype='pdf') as pdf:
            page_count = max(1, min(pdf.page_count, MAX_PAGES))
    except Exception:
        logger.exception('view_document: impossibile leggere %s %s', kind, doc_id)

    if not request.user.is_staff:
        if kind == 'cedolino':
            track_payslip_open(request, doc)
        else:
            track_cud_open(request, doc)

    response = render(request, 'portal/document_viewer.html', {
        'title': title,
        'kind': kind,
        'doc': doc,
        'filename': filename,
        'raw_url': raw_url,
        'pages': range(1, page_count + 1),
    })
    return _disable_response_cache(response)


@login_required
def document_page_image(request, kind, doc_id, page):
    doc, _, _, _ = _get_document(request, kind, doc_id)
    if doc is None:
        return HttpResponse('Non autorizzato', status=403)
    try:
        import fitz
        with fitz.open(stream=_read_pdf(doc), filetype='pdf') as pdf:
            if page < 1 or page > min(pdf.page_count, MAX_PAGES):
                raise Http404
            pix = pdf[page - 1].get_pixmap(dpi=144)
            png = pix.tobytes('png')
    except Http404:
        raise
    except Exception:
        logger.exception('document_page_image: errore %s %s p%s', kind, doc_id, page)
        return HttpResponse('Errore nel recupero della pagina', status=500)
    return _disable_response_cache(HttpResponse(png, content_type='image/png'))
