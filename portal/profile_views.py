"""Foto profilo del dipendente: caricamento dal telefono e visualizzazione protetta."""

import io
import logging

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Employee
from .views import _create_audit_event

logger = logging.getLogger(__name__)

MAX_UPLOAD = 15 * 1024 * 1024
SIZE = 512


def make_avatar(data):
    """Foto qualsiasi -> JPEG quadrato 512x512 centrato, orientato correttamente."""
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert('RGB')
    side = min(img.width, img.height)
    if side < 80:
        raise ValueError('Foto troppo piccola.')
    left = (img.width - side) // 2
    top = (img.height - side) // 2
    # Nei ritratti verticali il viso è di solito nella parte alta: sposta un po' in su il ritaglio.
    if img.height > img.width:
        top = max(0, int((img.height - side) * 0.3))
    img = img.crop((left, top, left + side, top + side)).resize((SIZE, SIZE), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, 'JPEG', quality=86, optimize=True)
    return out.getvalue()


@login_required
def employee_profile(request):
    employee = Employee.objects.filter(user=request.user).first()
    if not employee:
        return redirect('dashboard')
    if request.method == 'POST':
        if request.POST.get('action') == 'remove':
            old = employee.photo.name if employee.photo else ''
            employee.photo = ''
            employee.photo_updated_at = timezone.now()
            employee.save(update_fields=['photo', 'photo_updated_at'])
            if old:
                try:
                    employee.photo.storage.delete(old)
                except Exception:
                    logger.exception('foto profilo: impossibile eliminare %s', old)
            return JsonResponse({'ok': True})
        upload = request.FILES.get('photo')
        if not upload or upload.size > MAX_UPLOAD:
            return JsonResponse({'ok': False, 'error': 'Foto mancante o troppo grande.'}, status=400)
        try:
            jpg = make_avatar(upload.read())
        except Exception:
            return JsonResponse({'ok': False, 'error': 'Non riesco a leggere questa foto: provane un\'altra.'}, status=400)
        old = employee.photo.name if employee.photo else ''
        employee.photo.save(f'emp{employee.id}-{timezone.now():%Y%m%d%H%M%S%f}.jpg', ContentFile(jpg), save=False)
        employee.photo_updated_at = timezone.now()
        employee.save(update_fields=['photo', 'photo_updated_at'])
        if old and old != employee.photo.name:
            try:
                employee.photo.storage.delete(old)
            except Exception:
                logger.exception('foto profilo: impossibile eliminare %s', old)
        _create_audit_event(request, 'profile_photo_updated', employee=employee, metadata={})
        return JsonResponse({'ok': True})
    return render(request, 'portal/employee_profile.html', {'employee': employee})


@login_required
def profile_photo(request, emp_id):
    """Foto profilo: la vede il dipendente stesso e l'amministrazione."""
    employee = get_object_or_404(Employee, id=emp_id)
    if not request.user.is_staff and employee.user_id != request.user.id:
        return HttpResponse('Non autorizzato', status=403)
    if not employee.photo:
        raise Http404
    try:
        employee.photo.open('rb')
        try:
            data = employee.photo.read()
        finally:
            employee.photo.close()
    except Exception:
        raise Http404
    response = HttpResponse(data, content_type='image/jpeg')
    response['Cache-Control'] = 'private, max-age=86400'
    return response
