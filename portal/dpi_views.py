import os
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from . import dpi, push
from .models import (
    DPI_MODE_IN_PERSON,
    DPI_MODE_REMOTE,
    DPI_STATUS_CANCELLED,
    DPI_STATUS_PENDING,
    DPI_STATUS_SIGNED,
    DpiDelivery,
    Employee,
    PushSubscription,
)
from .views import _build_protected_file_response, _create_audit_event


def _sign_delivery(request, delivery, signature_png, mode):
    """Genera il PDF firmato e segna la consegna come firmata."""
    today = timezone.localdate()
    pdf_bytes = dpi.build_pdf(
        employee_name=delivery.employee.full_name,
        delivered_on=today,
        items=delivery.items,
        signature_png=signature_png,
    )
    delivery.pdf.save(
        f'consegna-dpi-{delivery.employee_id}-{today:%Y%m%d}.pdf', ContentFile(pdf_bytes), save=False
    )
    delivery.status = DPI_STATUS_SIGNED
    delivery.mode = mode
    delivery.delivered_on = today
    delivery.signed_at = timezone.now()
    delivery.signed_ip = request.META.get('REMOTE_ADDR') or None
    delivery.signed_user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    delivery.save()
    _create_audit_event(
        request, 'dpi_signed', employee=delivery.employee,
        metadata={'dpi_delivery_id': delivery.id, 'mode': mode, 'items': [i['text'] for i in delivery.items]},
    )


@login_required
def admin_dpi(request):
    """Pagina dedicata: scelta dipendente, DPI, firma subito o invio al dipendente, storico."""
    if not request.user.is_staff:
        return redirect('dashboard')

    employees = Employee.objects.select_related('user').order_by('last_name', 'first_name')
    error = None
    selected_id = request.POST.get('employee') or request.GET.get('employee') or ''

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'cancel':
            delivery = get_object_or_404(DpiDelivery, id=request.POST.get('delivery_id'), status=DPI_STATUS_PENDING)
            delivery.status = DPI_STATUS_CANCELLED
            delivery.save(update_fields=['status'])
            _create_audit_event(request, 'dpi_cancelled', employee=delivery.employee,
                                metadata={'dpi_delivery_id': delivery.id})
            return redirect(f"{reverse('admin_dpi')}?outcome=cancelled")

        if action == 'test_push':
            employee = Employee.objects.select_related('user').filter(id=selected_id).first() if str(selected_id).isdigit() else None
            if not employee:
                error = 'Scegli il dipendente a cui mandare la notifica di prova.'
            else:
                sent = push.send_to_user(employee.user, title='Notifica di prova',
                                         body='Le notifiche del portale San Vincenzo funzionano.',
                                         url=reverse('employee_dpi'), tag='prova')
                devices = push.describe_user_devices(employee.user)
                return render(request, 'portal/admin_dpi.html', _admin_dpi_context(
                    request, selected_id, None, None, push_test={'employee': employee, 'sent': sent, 'devices': devices,
                               'account': employee.user.get_username(), 'recent': push.recent_devices()}))

        if action in ('sign_now', 'send'):
            employee = Employee.objects.filter(id=selected_id).first() if str(selected_id).isdigit() else None
            items = dpi.build_items(request.POST)
            try:
                if not employee:
                    raise dpi.DpiError('Scegli il dipendente.')
                if not items:
                    raise dpi.DpiError('Seleziona almeno un DPI.')
                signature_png = dpi.decode_signature(request.POST.get('signature')) if action == 'sign_now' else None
            except dpi.DpiError as exc:
                error = str(exc)
            else:
                delivery = DpiDelivery.objects.create(
                    employee=employee, items=items, created_by=request.user, status=DPI_STATUS_PENDING,
                    mode=DPI_MODE_IN_PERSON if action == 'sign_now' else DPI_MODE_REMOTE,
                )
                if action == 'sign_now':
                    _sign_delivery(request, delivery, signature_png, DPI_MODE_IN_PERSON)
                    return redirect('open_dpi', dpi_id=delivery.id)
                delivery.notified_devices = push.send_to_user(
                    employee.user,
                    title='Consegna DPI da firmare',
                    body='Hai una consegna di dispositivi di protezione da firmare: tocca per firmare.',
                    url=reverse('employee_dpi_sign', args=[delivery.id]),
                    tag=f'dpi-{delivery.id}',
                )
                delivery.save(update_fields=['notified_devices'])
                _create_audit_event(request, 'dpi_sent_for_signature', employee=employee,
                                    metadata={'dpi_delivery_id': delivery.id, 'items': [i['text'] for i in items],
                                              'notified_devices': delivery.notified_devices})
                if delivery.notified_devices:
                    outcome = 'sent_push'
                elif employee.user.push_subscriptions.exists():
                    outcome = 'sent_push_failed'
                else:
                    outcome = 'sent'
                return redirect(f"{reverse('admin_dpi')}?outcome={outcome}")

    outcome = request.GET.get('outcome')
    feedback = {
        'sent': 'Consegna inviata: il dipendente la troverà da firmare nel suo account. '
                'Non ha attivato le notifiche, quindi la vedrà al prossimo accesso.',
        'sent_push': 'Consegna inviata e notifica arrivata sul telefono del dipendente.',
        'sent_push_failed': 'Consegna inviata, ma la notifica non è partita. Scegli il dipendente e usa «Prova notifica» per vedere l\'errore.',
        'cancelled': 'Richiesta di firma annullata.',
    }.get(outcome)

    return render(request, 'portal/admin_dpi.html', _admin_dpi_context(request, selected_id, error, feedback))


def _admin_dpi_context(request, selected_id, error, feedback, push_test=None):
    employees = Employee.objects.select_related('user').order_by('last_name', 'first_name')
    status_filter = request.GET.get('stato', '')
    history = DpiDelivery.objects.select_related('employee').exclude(status=DPI_STATUS_CANCELLED)
    if status_filter in (DPI_STATUS_PENDING, DPI_STATUS_SIGNED):
        history = history.filter(status=status_filter)
    page = Paginator(history, 30).get_page(request.GET.get('page'))

    return {
        'employees': employees,
        'push_test': push_test,
        'selected_id': str(selected_id),
        'standard_items': dpi.STANDARD_ITEMS,
        'error': error,
        'feedback': feedback,
        'today': date.today(),
        'posted': request.POST if request.method == 'POST' else None,
        'page': page,
        'status_filter': status_filter,
        'pending_count': DpiDelivery.objects.filter(status=DPI_STATUS_PENDING).count(),
        'push_user_ids': set(PushSubscription.objects.values_list('user_id', flat=True)),
        'dpi_rules': _rules_for_form(),
        'rules_saved': request.GET.get('durate') == '1',
    }


def _rules_for_form():
    from . import dpi_stats
    current = dpi_stats.rules()
    return [{'label': label, 'name': 'days_' + label.lower().replace(' ', '_'), 'days': current.get(label)}
            for label in dpi_stats.DEFAULT_DAYS]


@login_required
def admin_employee_dpi(request, emp_id):
    """Vecchio indirizzo dalla scheda dipendente: porta alla pagina dedicata con il dipendente già scelto."""
    if not request.user.is_staff:
        return redirect('dashboard')
    return redirect(f"{reverse('admin_dpi')}?employee={emp_id}")


def _own_employee(request):
    return Employee.objects.filter(user=request.user).first()


@login_required
def employee_dpi(request):
    """Area dipendente: consegne da firmare e già firmate."""
    employee = _own_employee(request)
    if not employee:
        return redirect('dashboard')
    deliveries = employee.dpi_deliveries.exclude(status=DPI_STATUS_CANCELLED)
    return render(request, 'portal/employee_dpi.html', {
        'employee': employee,
        'pending': deliveries.filter(status=DPI_STATUS_PENDING),
    })


@login_required
def employee_dpi_sign(request, dpi_id):
    employee = _own_employee(request)
    if not employee:
        return redirect('dashboard')
    delivery = get_object_or_404(DpiDelivery, id=dpi_id, employee=employee)
    if delivery.status != DPI_STATUS_PENDING:
        return redirect('employee_dpi')

    error = None
    if request.method == 'POST':
        try:
            signature_png = dpi.decode_signature(request.POST.get('signature'))
        except dpi.DpiError as exc:
            error = str(exc)
        else:
            _sign_delivery(request, delivery, signature_png, DPI_MODE_REMOTE)
            return redirect(f"{reverse('employee_dpi')}?outcome=signed")

    return render(request, 'portal/employee_dpi_sign.html', {
        'employee': employee,
        'delivery': delivery,
        'error': error,
        'today': timezone.localdate(),
    })


@login_required
def open_dpi(request, dpi_id):
    # I PDF delle consegne DPI sono consultabili solo dall'amministrazione.
    if not request.user.is_staff:
        return HttpResponse('Non autorizzato', status=403)
    delivery = get_object_or_404(DpiDelivery, id=dpi_id)
    if not delivery.pdf:
        return HttpResponse('Documento non ancora firmato', status=404)
    try:
        name = os.path.basename(delivery.pdf.name) or f'consegna-dpi-{delivery.id}.pdf'
        return _build_protected_file_response(delivery.pdf, download_name=name)
    except Exception:
        return HttpResponse('Errore nel recupero del file', status=500)


@login_required
def admin_employee_dpi_archive(request, emp_id):
    """Tutte le consegne DPI firmate di un dipendente in un unico PDF (dalla più recente)."""
    import fitz

    from .models import Employee

    if not request.user.is_staff:
        return HttpResponse('Non autorizzato', status=403)
    employee = get_object_or_404(Employee, id=emp_id)
    deliveries = [d for d in DpiDelivery.objects.filter(employee=employee, status=DPI_STATUS_SIGNED)
                  .order_by('-delivered_on', '-id') if d.pdf]
    if not deliveries:
        return HttpResponse('Nessuna consegna DPI firmata per questo dipendente.', status=404)
    out = fitz.open()
    try:
        for d in deliveries:
            d.pdf.open('rb')
            try:
                data = d.pdf.read()
            finally:
                d.pdf.close()
            with fitz.open(stream=data, filetype='pdf') as src:
                out.insert_pdf(src)
        pdf = out.tobytes(garbage=3, deflate=True)
    finally:
        out.close()
    name = f'consegne-dpi-{(employee.last_name or "")}-{(employee.first_name or "")}'.strip('-').replace(' ', '_')
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{name or "consegne-dpi"}.pdf"'
    response['Cache-Control'] = 'no-store'
    _create_audit_event(request, 'dpi_archive_downloaded', employee=employee, metadata={'count': len(deliveries)})
    return response


@login_required
def admin_dpi_summary(request, emp_id):
    """Riquadro «Situazione DPI» di un dipendente (caricato nella pagina Consegna DPI quando lo scegli)."""
    from . import dpi_stats

    if not request.user.is_staff:
        return HttpResponse('Non autorizzato', status=403)
    employee = get_object_or_404(Employee, id=emp_id)
    response = render(request, 'portal/includes/dpi_summary.html',
                      {'employee': employee, 'items': dpi_stats.summary(employee)})
    response['Cache-Control'] = 'no-store'
    return response


@login_required
def admin_dpi_rules(request):
    """Salva ogni quanti giorni si può ridare ciascun DPI."""
    from . import dpi_stats
    from .models import DpiReplacementRule

    if not request.user.is_staff or request.method != 'POST':
        return redirect('admin_dpi')
    for label in dpi_stats.DEFAULT_DAYS:
        raw = (request.POST.get('days_' + label.lower().replace(' ', '_')) or '').strip()
        if not raw.isdigit():
            continue
        days = max(1, min(int(raw), 3650))
        DpiReplacementRule.objects.update_or_create(label=label, defaults={'days': days})
    _create_audit_event(request, 'dpi_rules_updated', metadata={})
    return redirect(reverse('admin_dpi') + '?durate=1#durate')
