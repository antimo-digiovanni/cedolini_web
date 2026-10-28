import logging
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from . import doc_scan, identity_docs, push
from .models import Employee, IdentityDocument
from .views import _create_audit_event, _disable_response_cache

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _own_employee(request):
    return Employee.objects.filter(user=request.user).first()


def _kind_or_404(kind):
    if kind not in identity_docs.KIND_LABELS:
        raise Http404
    return kind


# ------------------------------------------------------------------ dipendente

@login_required
def employee_documents(request):
    employee = _own_employee(request)
    if not employee:
        return redirect('dashboard')
    latest = identity_docs.latest_by_kind(employee)
    cards = []
    for kind, label in identity_docs.KINDS:
        doc = latest[kind]
        cards.append({'kind': kind, 'label': label, 'doc': doc, 'state': identity_docs.describe(doc, kind)})
    from datetime import timedelta

    from django.utils import timezone

    from .deadlines import describe as describe_deadline
    from .models import EmployeeDeadline

    recent = timezone.localdate() - timedelta(days=60)
    deadlines = [{'d': d, 'state': describe_deadline(d)} for d in
                 EmployeeDeadline.objects.filter(employee=employee).exclude(done_on__lt=recent)
                 .order_by('done_on', 'due_date')[:30]]
    return render(request, 'portal/employee_documents.html', {
        'employee': employee, 'cards': cards, 'sent': request.GET.get('inviato') == '1', 'deadlines': deadlines,
    })


@login_required
def employee_document_upload(request, kind):
    kind = _kind_or_404(kind)
    employee = _own_employee(request)
    if not employee:
        return redirect('dashboard')

    if request.method == 'POST':
        def fail(msg, status=400):
            return JsonResponse({'ok': False, 'error': msg}, status=status)

        front, back = request.FILES.get('front'), request.FILES.get('back')
        if not front or not back:
            return fail('Servono entrambe le foto, fronte e retro.')
        if front.size > MAX_UPLOAD_BYTES or back.size > MAX_UPLOAD_BYTES:
            return fail('Le foto sono troppo grandi.')
        try:
            expiry = date.fromisoformat(request.POST.get('expiry_date', ''))
        except ValueError:
            return fail('Inserisci la data di scadenza del documento.')
        if expiry < timezone.localdate():
            return fail('Il documento risulta scaduto: carica quello valido.')
        if expiry > timezone.localdate() + timedelta(days=365 * 15):
            return fail('Controlla la data di scadenza.')
        try:
            front_jpg, front_cropped = _process(front, request.POST.get('front_rect'))
            back_jpg, back_cropped = _process(back, request.POST.get('back_rect'))
        except doc_scan.ScanError as exc:
            return fail(str(exc))
        if not front_cropped or not back_cropped:
            side = 'del fronte' if not front_cropped else 'del retro'
            if not front_cropped and not back_cropped:
                side = 'di fronte e retro'
            return fail(f'Nella foto {side} il documento non si riconosce bene: rifalla più da vicino, '
                        'con il documento intero dentro il riquadro, su un piano scuro e con buona luce.')

        stamp = timezone.now().strftime('%Y%m%d%H%M%S')
        doc = IdentityDocument(employee=employee, kind=kind, expiry_date=expiry,
                               front_cropped=front_cropped, back_cropped=back_cropped)
        doc.front_image.save(f'{kind}-{employee.id}-{stamp}-fronte.jpg', ContentFile(front_jpg), save=False)
        doc.back_image.save(f'{kind}-{employee.id}-{stamp}-retro.jpg', ContentFile(back_jpg), save=False)
        doc.save()
        _create_audit_event(request, 'identity_document_uploaded', employee=employee,
                            metadata={'document_id': doc.id, 'kind': kind, 'expiry': str(expiry),
                                      'cropped': [front_cropped, back_cropped]})
        _notify_admins(doc)
        return JsonResponse({'ok': True, 'redirect': reverse('employee_documents') + '?inviato=1'})

    this_year = timezone.localdate().year
    return render(request, 'portal/employee_document_upload.html', {
        'employee': employee, 'kind': kind, 'label': identity_docs.KIND_LABELS[kind],
        'today': timezone.localdate(),
        'days': range(1, 32), 'months': list(enumerate(MONTHS_IT, start=1)),
        'years': range(this_year, this_year + 16),
    })


MONTHS_IT = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto',
             'Settembre', 'Ottobre', 'Novembre', 'Dicembre']


def _process(upload, rect_json):
    """Foto dalla fotocamera del portale (con il riquadro) o dalla Galleria (ricerca libera)."""
    import json
    data = upload.read()
    if rect_json:
        try:
            rect = [float(v) for v in json.loads(rect_json)]
            if len(rect) != 4:
                raise ValueError
        except (ValueError, TypeError):
            raise doc_scan.ScanError('Foto non valida: rifalla dalla fotocamera del portale.')
        return doc_scan.process_guided_photo(data, rect)
    return doc_scan.process_photo(data)


@login_required
def employee_document_preview(request):
    """Anteprima dopo lo scatto: restituisce la foto già raddrizzata e ritagliata come verrà salvata."""
    if request.method != 'POST' or not _own_employee(request):
        return HttpResponse(status=405 if request.method != 'POST' else 403)
    photo = request.FILES.get('photo')
    if not photo or photo.size > MAX_UPLOAD_BYTES:
        return JsonResponse({'ok': False, 'error': 'Foto mancante o troppo grande.'}, status=400)
    try:
        jpg, cropped = _process(photo, request.POST.get('rect'))
    except doc_scan.ScanError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    if not cropped:
        return JsonResponse({'ok': False, 'error': 'Il documento non si riconosce bene: rifai la foto più da vicino, '
                                                    'con il documento intero dentro il riquadro.'}, status=400)
    return _disable_response_cache(HttpResponse(jpg, content_type='image/jpeg'))


def _notify_admins(doc):
    """Notifica push agli admin che hanno attivato le notifiche."""
    from django.contrib.auth.models import User
    for admin in User.objects.filter(is_staff=True, push_subscriptions__isnull=False).distinct():
        push.notify_later(admin.id, title='Documento da verificare',
                          body=f'{doc.employee.full_name} ha caricato: {doc.get_kind_display()}.',
                          url=reverse('admin_document_detail', args=[doc.id]), tag=f'doc-verifica-{doc.id}')


# ------------------------------------------------------------------ immagini e PDF (protetti)

@login_required
def document_image(request, doc_id, side):
    doc = get_object_or_404(IdentityDocument.objects.select_related('employee'), id=doc_id)
    if not request.user.is_staff and doc.employee.user_id != request.user.id:
        return HttpResponse('Non autorizzato', status=403)
    field = {'fronte': doc.front_image, 'retro': doc.back_image}.get(side)
    if field is None:
        raise Http404
    field.open('rb')
    try:
        data = field.read()
    finally:
        field.close()
    return _disable_response_cache(HttpResponse(data, content_type='image/jpeg'))


@login_required
def admin_document_pdf(request, doc_id):
    doc = get_object_or_404(IdentityDocument.objects.select_related('employee', 'reviewed_by'), id=doc_id)
    if not request.user.is_staff and doc.employee.user_id != request.user.id:
        return HttpResponse('Non autorizzato', status=403)
    pdf = identity_docs.build_pdf(doc)
    name = f'{doc.kind}-{(doc.employee.last_name or "")}-{(doc.employee.first_name or "")}'.strip('-').replace(' ', '_')
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{name or "documento"}.pdf"'
    _create_audit_event(request, 'identity_document_downloaded', employee=doc.employee, metadata={'document_id': doc.id})
    return _disable_response_cache(response)


# ------------------------------------------------------------------ amministrazione

FILTERS = {
    '': 'Tutti',
    'caricati': 'Hanno caricato',
    'verificare': 'Da verificare',
    'scadenza': 'In scadenza o scaduti',
    'mancanti': "Senza carta d'identità",
}


@login_required
def admin_documents(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    employees = (Employee.objects.select_related('user').prefetch_related('identity_documents')
                 .order_by('last_name', 'first_name'))
    rows, counts = [], {'caricati': 0, 'verificare': 0, 'scadenza': 0, 'mancanti': 0}
    q = (request.GET.get('q') or '').strip().lower()
    flt = request.GET.get('filtro', '')
    for emp in employees:
        latest = identity_docs.latest_by_kind(emp)
        cells = []
        tags = set()
        for kind, label in identity_docs.KINDS:
            st = identity_docs.describe(latest[kind], kind)
            cells.append({'kind': kind, 'doc': latest[kind], 'state': st})
            if latest[kind] is not None:
                tags.add('caricati')
            if st['code'] == 'pending':
                tags.add('verificare')
            if st['code'] in ('expiring', 'expired'):
                tags.add('scadenza')
            if kind == 'ci' and st['code'] in ('missing', 'rejected'):
                tags.add('mancanti')
        for t in tags:
            counts[t] += 1
        if q and q not in emp.full_name.lower():
            continue
        if flt and flt not in tags:
            continue
        rows.append({'employee': emp, 'cells': cells})
    return render(request, 'portal/admin_documents.html', {
        'rows': rows, 'counts': counts, 'filters': FILTERS, 'filtro': flt, 'q': request.GET.get('q', ''),
    })


@login_required
def admin_document_detail(request, doc_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    doc = get_object_or_404(IdentityDocument.objects.select_related('employee__user', 'reviewed_by'), id=doc_id)
    error = None

    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ('approve', 'reject'):
            if request.POST.get('expiry_date'):
                try:
                    doc.expiry_date = date.fromisoformat(request.POST['expiry_date'])
                except ValueError:
                    error = 'Data di scadenza non valida.'
            note = (request.POST.get('review_note') or '').strip()[:255]
            if action == 'reject' and not note:
                error = 'Scrivi il motivo del rifiuto: il dipendente lo vedrà.'
            if not error:
                doc.status = doc.STATUS_APPROVED if action == 'approve' else doc.STATUS_REJECTED
                doc.review_note = note if action == 'reject' else ''
                doc.reviewed_by = request.user
                doc.reviewed_at = timezone.now()
                doc.expiry_notified_on = None
                doc.save()
                _create_audit_event(request, f'identity_document_{action}d', employee=doc.employee,
                                    metadata={'document_id': doc.id, 'note': note})
                if action == 'reject':
                    push.notify_later(doc.employee.user_id, title='Documento da rifare',
                                      body=f'La tua {doc.get_kind_display().lower()} non è stata accettata: {note}',
                                      url=reverse('employee_documents'), tag=f'doc-{doc.kind}')
                return redirect(reverse('admin_document_detail', args=[doc.id]) + f'?esito={action}')
        elif action == 'rotate':
            side = request.POST.get('side')
            field = {'fronte': doc.front_image, 'retro': doc.back_image}.get(side)
            degrees = 180 if request.POST.get('degrees') == '180' else 90
            if field is not None:
                field.open('rb')
                try:
                    data = doc_scan.rotate_jpeg(field.read(), degrees)
                finally:
                    field.close()
                old_name = field.name
                # Nome nuovo a ogni rotazione: sullo storage online un file con lo stesso nome
                # verrebbe sovrascritto e poi cancellato insieme alla "vecchia" versione.
                base = old_name.rsplit('/', 1)[-1].rsplit('.', 1)[0].split('-r', 1)[0]
                new_name = f"{base}-r{timezone.now():%Y%m%d%H%M%S%f}.jpg"
                field.save(new_name, ContentFile(data), save=True)
                if field.name != old_name:
                    try:
                        field.storage.delete(old_name)
                    except Exception:
                        logger.exception('rotazione: impossibile eliminare la vecchia foto %s', old_name)
            return redirect('admin_document_detail', doc_id=doc.id)

    history = doc.employee.identity_documents.filter(kind=doc.kind).exclude(id=doc.id)[:10]
    esito = {'approve': 'Documento approvato.', 'reject': 'Documento rifiutato: il dipendente è stato avvisato.'}.get(
        request.GET.get('esito'))
    return render(request, 'portal/admin_document_detail.html', {
        'doc': doc, 'state': identity_docs.describe(doc, doc.kind), 'history': history,
        'error': error, 'esito': esito, 'stamp': int(timezone.now().timestamp()),
    })
