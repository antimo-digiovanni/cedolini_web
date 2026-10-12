import os
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from . import dpi
from .models import DpiDelivery, Employee
from .views import _build_protected_file_response, _create_audit_event


@login_required
def admin_employee_dpi(request, emp_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    employee = get_object_or_404(Employee, id=emp_id)
    error = None

    if request.method == 'POST':
        items = dpi.build_items(request.POST)
        try:
            if not items:
                raise dpi.DpiError('Seleziona almeno un DPI.')
            signature_png = dpi.decode_signature(request.POST.get('signature'))
        except dpi.DpiError as exc:
            error = str(exc)
        else:
            today = date.today()
            pdf_bytes = dpi.build_pdf(
                employee_name=employee.full_name,
                delivered_on=today,
                items=items,
                signature_png=signature_png,
            )
            delivery = DpiDelivery(employee=employee, delivered_on=today, items=items, created_by=request.user)
            delivery.pdf.save(f'consegna-dpi-{employee.id}-{today:%Y%m%d}.pdf', ContentFile(pdf_bytes), save=False)
            delivery.save()
            _create_audit_event(
                request, 'dpi_delivered', employee=employee,
                metadata={'dpi_delivery_id': delivery.id, 'items': [i['text'] for i in items]},
            )
            return redirect('open_dpi', dpi_id=delivery.id)

    return render(request, 'portal/admin_employee_dpi.html', {
        'employee': employee,
        'standard_items': dpi.STANDARD_ITEMS,
        'error': error,
        'today': date.today(),
        'posted': request.POST if request.method == 'POST' else None,
    })


@login_required
def open_dpi(request, dpi_id):
    delivery = get_object_or_404(DpiDelivery, id=dpi_id)
    if not request.user.is_staff and delivery.employee.user != request.user:
        return HttpResponse('Non autorizzato', status=403)
    try:
        name = os.path.basename(delivery.pdf.name) or f'consegna-dpi-{delivery.id}.pdf'
        return _build_protected_file_response(delivery.pdf, download_name=name)
    except Exception:
        return HttpResponse('Errore nel recupero del file', status=500)
