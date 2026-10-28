"""Documenti di identità e patente: stato, scadenze, PDF per l'ufficio del personale."""

import io
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

EXPIRY_WARNING_DAYS = 30
KINDS = [('ci', "Carta d'identità"), ('patente', 'Patente di guida')]
KIND_LABELS = dict(KINDS)


def latest_by_kind(employee):
    """Ultimo documento caricato per ogni tipo: {'ci': doc|None, 'patente': doc|None}."""
    out = {k: None for k, _ in KINDS}
    for doc in employee.identity_documents.all():  # ordinati dal più recente
        if out.get(doc.kind) is None:
            out[doc.kind] = doc
    return out


def describe(doc, kind):
    """Stato leggibile di un documento (o della sua mancanza)."""
    today = timezone.localdate()
    if doc is None:
        return {'code': 'missing', 'label': 'Da caricare' if kind == 'ci' else 'Non caricata',
                'detail': 'Fronte e retro', 'tone': 'warn' if kind == 'ci' else 'muted'}
    if doc.status == doc.STATUS_PENDING:
        return {'code': 'pending', 'label': 'In verifica', 'tone': 'info',
                'detail': f'Inviato il {doc.uploaded_at:%d/%m/%Y}'}
    if doc.status == doc.STATUS_REJECTED:
        note = f': {doc.review_note}' if doc.review_note else ''
        return {'code': 'rejected', 'label': 'Da rifare', 'tone': 'danger', 'detail': f'Foto non accettate{note}'}
    if doc.expiry_date < today:
        return {'code': 'expired', 'label': 'Scaduto', 'tone': 'danger', 'detail': f'Scaduto il {doc.expiry_date:%d/%m/%Y}'}
    if doc.expiry_date <= today + timedelta(days=EXPIRY_WARNING_DAYS):
        days = (doc.expiry_date - today).days
        return {'code': 'expiring', 'label': 'In scadenza', 'tone': 'danger',
                'detail': f'Scade il {doc.expiry_date:%d/%m/%Y} (tra {days} giorn{"o" if days == 1 else "i"})'}
    return {'code': 'valid', 'label': 'Valido', 'tone': 'ok', 'detail': f'Scade il {doc.expiry_date:%d/%m/%Y}'}


def needs_attention(employee):
    """Per l'avviso in dashboard dipendente: lista di (tipo, stato) che richiedono un'azione."""
    out = []
    for kind, doc in latest_by_kind(employee).items():
        st = describe(doc, kind)
        if st['code'] in ('rejected', 'expired', 'expiring') or (kind == 'ci' and st['code'] == 'missing'):
            out.append((KIND_LABELS[kind], st))
    return out


def build_pdf(doc):
    """PDF A4 con i dati del caricamento e le foto di fronte e retro."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from PIL import Image

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    wp, hp = A4
    pdf.setTitle(f'{doc.get_kind_display()} - {doc.employee.full_name}')
    from .dpi import LETTERHEAD_ASPECT, LETTERHEAD_PATH

    top_y = hp - 12 * mm
    if LETTERHEAD_PATH.exists():
        lh_w = 150 * mm
        lh_h = lh_w / LETTERHEAD_ASPECT
        pdf.drawImage(str(LETTERHEAD_PATH), (wp - lh_w) / 2, top_y - lh_h, width=lh_w, height=lh_h, mask='auto')
        top_y -= lh_h + 3 * mm
        pdf.setStrokeGray(0.75)
        pdf.setLineWidth(0.6)
        pdf.line(20 * mm, top_y, wp - 20 * mm, top_y)
    else:
        pdf.setFont('Helvetica-Bold', 11)
        pdf.drawString(20 * mm, top_y - 6 * mm, 'SAN VINCENZO S.R.L.')
        pdf.setFont('Helvetica', 9)
        pdf.drawString(20 * mm, top_y - 11 * mm, 'VIA B. CELLINI 154 GRUMO NEVANO (NAPOLI)')
        top_y -= 14 * mm
    pdf.setFont('Helvetica-Bold', 15)
    pdf.drawString(20 * mm, top_y - 9 * mm, doc.get_kind_display())

    uploaded = timezone.localtime(doc.uploaded_at)
    if doc.status == doc.STATUS_APPROVED and doc.reviewed_at:
        who = doc.reviewed_by.get_full_name() or doc.reviewed_by.get_username() if doc.reviewed_by else ''
        state = f'Approvato il {timezone.localtime(doc.reviewed_at):%d/%m/%Y}' + (f' da {who}' if who else '')
    else:
        state = doc.get_status_display()
    rows = [('Dipendente', doc.employee.full_name),
            ('Caricato il', f'{uploaded:%d/%m/%Y alle %H:%M}, dal portale dipendenti'),
            ('Scadenza', f'{doc.expiry_date:%d/%m/%Y}'),
            ('Stato', state)]
    y = top_y - 17 * mm
    for k, v in rows:
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(20 * mm, y, k)
        pdf.setFont('Helvetica', 10)
        pdf.drawString(58 * mm, y, v)
        y -= 6 * mm

    max_w = 85.6 * 1.2 * mm  # poco più grande del vero: leggibile e tutto in un foglio
    max_h = (y - 24 * mm) / 2 - 12 * mm
    top = y - 6 * mm
    for label, field in (('FRONTE', doc.front_image), ('RETRO', doc.back_image)):
        field.open('rb')
        try:
            img = Image.open(io.BytesIO(field.read())).convert('RGB')
        finally:
            field.close()
        cropped = doc.front_cropped if label == 'FRONTE' else doc.back_cropped
        if cropped:
            from .doc_scan import round_corners
            img = round_corners(img)  # vale anche per i documenti caricati prima di questa correzione
        k = min(max_w / img.width, max_h / img.height)
        w, h = img.width * k, img.height * k
        x0 = (wp - w) / 2
        pdf.setFont('Helvetica-Bold', 9)
        pdf.setFillGray(0.35)
        pdf.drawString(x0, top, label)
        pdf.setFillGray(0)
        out = io.BytesIO()
        img.save(out, 'JPEG', quality=85)
        out.seek(0)
        pdf.drawImage(ImageReader(out), x0, top - h - 3 * mm, width=w, height=h)
        pdf.setStrokeGray(0.75)
        if cropped:
            pdf.roundRect(x0, top - h - 3 * mm, w, h, radius=max(w, h) * 0.045)
        else:
            pdf.rect(x0, top - h - 3 * mm, w, h)
        top = top - h - 12 * mm

    pdf.setFont('Helvetica', 7.5)
    pdf.setFillGray(0.4)
    pdf.drawString(20 * mm, 12 * mm, 'Documento riservato - uso interno ufficio del personale. '
                   f'Copia generata dal portale San Vincenzo il {timezone.localdate():%d/%m/%Y}.')
    pdf.save()
    return buf.getvalue()


def run_expiry_notifications():
    """Avvisa (notifica push) i dipendenti con documento approvato in scadenza entro 30 giorni. Una volta sola."""
    from django.urls import reverse

    from . import push
    from .models import IdentityDocument

    today = timezone.localdate()
    limit = today + timedelta(days=EXPIRY_WARNING_DAYS)
    docs = (IdentityDocument.objects.select_related('employee__user')
            .filter(status=IdentityDocument.STATUS_APPROVED, expiry_date__lte=limit, expiry_notified_on__isnull=True))
    sent = 0
    for doc in docs:
        if latest_by_kind(doc.employee).get(doc.kind) != doc:
            continue  # ne ha già caricato uno più recente
        when = 'è scaduta' if doc.expiry_date < today else f'scade il {doc.expiry_date:%d/%m/%Y}'
        push.send_to_user(doc.employee.user, title='Documento in scadenza',
                          body=f'La tua {doc.get_kind_display().lower()} {when}. Carica quella nuova dal portale.',
                          url=reverse('employee_documents'), tag=f'doc-{doc.kind}')
        doc.expiry_notified_on = today
        doc.save(update_fields=['expiry_notified_on'])
        sent += 1
    return sent


_LAST_DAILY_CHECK = None


def maybe_run_daily_checks():
    """Esegue i controlli giornalieri al massimo una volta al giorno, in background (non serve un cron)."""
    from django.conf import settings
    from django.db import connection, transaction

    from .models import DailyTaskRun

    global _LAST_DAILY_CHECK
    today = timezone.localdate()
    if _LAST_DAILY_CHECK == today:
        return False  # già fatto oggi in questo processo: nessuna query
    _LAST_DAILY_CHECK = today
    try:
        with transaction.atomic():
            run, created = DailyTaskRun.objects.select_for_update().get_or_create(
                name='scadenze_documenti', defaults={'last_run': today})
            if not created:
                if run.last_run >= today:
                    return False
                run.last_run = today
                run.save(update_fields=['last_run'])
    except Exception:
        logger.exception('controlli giornalieri: impossibile registrare l\'esecuzione')
        return False

    def job():
        try:
            run_expiry_notifications()
        except Exception:
            logger.exception('controlli giornalieri: errore notifiche scadenze')
        finally:
            if getattr(settings, 'PUSH_ASYNC', True):
                connection.close()

    if getattr(settings, 'PUSH_ASYNC', True):
        import threading
        threading.Thread(target=job, daemon=True).start()
    else:
        job()
    return True
