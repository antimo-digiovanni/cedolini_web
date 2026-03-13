import os
import csv
import json
import math
import calendar
from collections import OrderedDict
from datetime import date
from datetime import datetime
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, FileResponse, HttpResponseRedirect, HttpResponsePermanentRedirect
from django.db import transaction, IntegrityError
from django.db.models import Count, Q
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.templatetags.static import static

from .models import (
    Employee,
    Payslip,
    PayslipView,
    ImportJob,
    InviteToken,
    Cud,
    CudView,
    WorkZone,
    EmployeeWorkZone,
    WorkSession,
    WorkMarkRequest,
)
from .models import AuditEvent
from django.core.paginator import Paginator

import logging
import secrets

from .utils_import import parse_payslip_filename
from .access import user_has_full_admin_access, user_has_today_markings_access, user_home_url_name

logger = logging.getLogger(__name__)


MONTH_LABELS_IT = {
    1: 'Gennaio',
    2: 'Febbraio',
    3: 'Marzo',
    4: 'Aprile',
    5: 'Maggio',
    6: 'Giugno',
    7: 'Luglio',
    8: 'Agosto',
    9: 'Settembre',
    10: 'Ottobre',
    11: 'Novembre',
    12: 'Dicembre',
}

MAX_SHIFT_DURATION_HOURS = 18


def _disable_response_cache(response):
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


# =========================================================
# Utility: Audit logging
# =========================================================

def _create_audit_event(request, action, *, employee=None, payslip=None, metadata=None):
    """Crea un AuditEvent di base con IP e user-agent.

    Usato per popolare la pagina "Storico azioni" con eventi
    significativi (apertura cedolino, import massivi, inviti, ecc.).
    """
    try:
        ip = request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT', '')
        AuditEvent.objects.create(
            action=action,
            actor_user=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            employee=employee,
            payslip=payslip,
            ip_address=ip,
            user_agent=ua,
            metadata=metadata or {},
        )
    except Exception:
        # Non bloccare il flusso se il log fallisce
        logger.exception("Errore nella creazione di AuditEvent (%s)", action)


def _send_out_of_zone_request_admin_notification(request_obj):
    recipients = [email for email in getattr(settings, 'ADMIN_NOTIFICATION_EMAILS', []) if email]
    if not recipients:
        return

    employee = request_obj.employee
    mark_type_label = dict(WorkMarkRequest.MARK_TYPE_CHOICES).get(request_obj.mark_type, request_obj.mark_type)
    app_base_url = getattr(settings, 'APP_BASE_URL', '').rstrip('/')
    admin_url = f"{app_base_url}/portal/admin-richieste-fuori-zona/" if app_base_url else '/portal/admin-richieste-fuori-zona/'

    subject = f"Nuova richiesta fuori zona - {employee.full_name}"
    body = (
        "E' stata inviata una nuova richiesta di marcatura fuori zona.\n\n"
        f"Dipendente: {employee.full_name}\n"
        f"Data lavoro: {request_obj.work_date:%d/%m/%Y}\n"
        f"Tipo: {mark_type_label}\n"
        f"Motivazione: {request_obj.reason}\n"
        f"Richiesta ID: {request_obj.id}\n\n"
        f"Apri lo storico richieste: {admin_url}\n"
    )

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        email.send(fail_silently=False)
    except Exception:
        logger.exception(
            'Errore invio notifica admin per richiesta fuori zona id=%s',
            request_obj.id,
        )


def _attach_payslip_display_period(payslip):
    display_month = payslip.month
    display_year = payslip.year

    try:
        _, _, parsed_month, parsed_year = parse_payslip_filename(os.path.basename(payslip.pdf.name))
        display_month = parsed_month
        display_year = parsed_year
    except Exception:
        pass

    payslip.display_month = display_month
    payslip.display_year = display_year
    payslip.display_month_name = MONTH_LABELS_IT.get(display_month, str(display_month))
    return payslip


# =========================================================
# HOME
# =========================================================

def home(request):
    if request.user.is_authenticated:
        return redirect(user_home_url_name(request.user))
    return render(request, 'site/home.html')


def public_home(request):
    return render(request, 'site/home.html')


def public_services(request):
    return render(request, 'site/services.html')


def public_digital_services(request):
    return render(request, 'site/digital_services.html')


def public_about(request):
    return render(request, 'site/about.html')


def public_machinery(request):
    return render(request, 'site/machinery.html')


def public_contacts(request):
    contact_email = 'antimo.digiovanni@sanvincenzosrl.com'
    form_data = {
        'name': '',
        'email': '',
        'phone': '',
        'subject': '',
        'message': '',
    }
    contact_error = None
    contact_success = False

    if request.method == 'POST':
        form_data = {
            'name': request.POST.get('name', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'phone': request.POST.get('phone', '').strip(),
            'subject': request.POST.get('subject', '').strip(),
            'message': request.POST.get('message', '').strip(),
        }

        if not form_data['name'] or not form_data['email'] or not form_data['message']:
            contact_error = 'Compila almeno nome, email e messaggio.'
        else:
            email_subject = form_data['subject'] or 'Nuova richiesta dal sito San Vincenzo SRL'
            email_body = (
                'Nuova richiesta ricevuta dal sito web.\n\n'
                f"Nome: {form_data['name']}\n"
                f"Email: {form_data['email']}\n"
                f"Telefono: {form_data['phone'] or 'Non indicato'}\n"
                f"Oggetto: {form_data['subject'] or 'Non indicato'}\n\n"
                'Messaggio:\n'
                f"{form_data['message']}\n"
            )

            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '') or 'noreply@sanvincenzosrl.com'

            try:
                mail = EmailMultiAlternatives(
                    subject=email_subject,
                    body=email_body,
                    from_email=from_email,
                    to=[contact_email],
                    reply_to=[form_data['email']],
                )
                mail.send(fail_silently=False)
                contact_success = True
                form_data = {
                    'name': '',
                    'email': '',
                    'phone': '',
                    'subject': '',
                    'message': '',
                }
            except Exception:
                logger.exception('Errore invio richiesta contatti sito pubblico')
                contact_error = 'Invio non riuscito al momento. Puoi scriverci direttamente via email o telefono.'

    return render(request, 'site/contacts.html', {
        'contact_email': contact_email,
        'form_data': form_data,
        'contact_error': contact_error,
        'contact_success': contact_success,
    })


def sitemap_xml(request):
    pages = [
        '',
        'chi-siamo/',
        'servizi/',
        'servizi-digitali/',
        'macchinari/',
        'contatti/',
        'login/',
    ]
    base_url = request.build_absolute_uri('/').rstrip('/')
    xml_items = []
    for page in pages:
        xml_items.append(
            f"<url><loc>{base_url}/{page}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + ''.join(xml_items) +
        '</urlset>'
    )
    return HttpResponse(xml, content_type='application/xml')


def robots_txt(request):
    base_url = request.build_absolute_uri('/').rstrip('/')
    content = (
        'User-agent: *\n'
        'Allow: /\n\n'
        f'Sitemap: {base_url}/sitemap.xml\n'
    )
    return HttpResponse(content, content_type='text/plain')


def site_webmanifest(request):
    """Manifest PWA per installazione su schermata Home Android."""
    icon_192_url = request.build_absolute_uri(static('portal/icons/icon-192.png'))
    icon_512_url = request.build_absolute_uri(static('portal/icons/icon-512.png'))
    manifest = {
        "name": "San Vincenzo S.R.L.",
        "short_name": "San Vincenzo",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f5f8ff",
        "theme_color": "#0f172a",
        "description": "Servizi professionali e soluzioni operative per aziende.",
        "icons": [
            {
                "src": icon_192_url,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": icon_512_url,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return HttpResponse(
        json.dumps(manifest),
        content_type='application/manifest+json',
    )


def google_site_verification(request):
    """Serve il file di verifica Search Console al percorso richiesto da Google."""
    return HttpResponse(
        'google-site-verification: googlee8ce7f16b7b5fed5.html',
        content_type='text/plain',
    )


def favicon_ico(request):
    """Compatibilita browser: favicon richiesta su /favicon.ico."""
    return HttpResponsePermanentRedirect(static('portal/icons/icon-192.png'))


def favicon_32_png(request):
    """Compatibilita launcher: icona 32x32 su path standard."""
    return HttpResponsePermanentRedirect(static('portal/icons/icon-192.png'))


def favicon_16_png(request):
    """Compatibilita launcher: icona 16x16 su path standard."""
    return HttpResponsePermanentRedirect(static('portal/icons/icon-192.png'))


def apple_touch_icon(request):
    """Compatibilita iOS: apple-touch-icon su root path."""
    return HttpResponsePermanentRedirect(static('portal/icons/apple-touch-icon.png'))


def apple_touch_icon_precomposed(request):
    """Compatibilita iOS legacy: apple-touch-icon-precomposed su root path."""
    return HttpResponsePermanentRedirect(static('portal/icons/apple-touch-icon.png'))


# =========================================================
# REGISTER VIA TOKEN
# =========================================================

def register_with_token(request, token):
    invite = get_object_or_404(InviteToken, token=token)

    if not invite.is_valid():
        return HttpResponse("Token non valido o scaduto.", status=400)

    employee = invite.employee
    user = employee.user

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")
        privacy_accepted = request.POST.get("privacy_accepted") == "on"

        if not first_name or not last_name or not email or not password:
            return render(request, "portal/register.html", {
                "employee": employee,
                "error": "Compila tutti i campi"
            })

        if len(password) < 8:
            return render(request, "portal/register.html", {
                "employee": employee,
                "error": "Password troppo corta (min 8 caratteri)"
            })

        if password != confirm:
            return render(request, "portal/register.html", {
                "employee": employee,
                "error": "Le password non coincidono"
            })

        if not privacy_accepted:
            return render(request, "portal/register.html", {
                "employee": employee,
                "error": "Devi accettare l'informativa privacy per completare la registrazione."
            })

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.set_password(password)
        user.is_active = True
        user.save()

        employee.first_name = first_name
        employee.last_name = last_name
        employee.email_invio = email
        employee.must_change_password = False
        employee.privacy_accepted = True
        employee.privacy_accepted_at = timezone.now()
        employee.save()

        invite.mark_used()

        return redirect("/login/")

    return render(request, "portal/register.html", {
        "employee": employee
    })


# =========================================================
# DASHBOARD DIPENDENTE
# =========================================================

@login_required
def dashboard(request):
    logger.info("dashboard START user=%s", getattr(request.user, "username", None))

    # Se uno staff arriva direttamente su /portal/, portalo alla dashboard admin.
    if request.user.is_staff:
        return redirect('admin_dashboard')

    employee = Employee.objects.filter(user=request.user).first()
    if not employee:
        logger.warning("dashboard: employee profile missing for user=%s", request.user.id)
        return HttpResponse(
            "Profilo dipendente non trovato. Contatta l'amministratore.",
            status=403,
        )

    logger.info("dashboard employee_id=%s", getattr(employee, "id", None))

    logger.info("constructing payslips queryset")
    payslips = (
        Payslip.objects
        .filter(employee=employee)
        .prefetch_related("payslipview_set")
        .order_by('-year', '-month')
    )

    logger.info("queryset constructed — forcing evaluation with .count()")
    try:
        count = payslips.count()
        logger.info("payslips.count=%d", count)
    except Exception:
        logger.exception("Error while evaluating payslips queryset")

    grouped = {}
    logger.info("entering loop over payslips")
    for idx, p in enumerate(payslips):
        if idx < 5:
            logger.info("processing payslip id=%s year=%s month=%s", getattr(p, "id", None), getattr(p, "year", None), getattr(p, "month", None))

        first_view = None
        if p.payslipview_set.all():
            first_view = p.payslipview_set.order_by('viewed_at').first()

        p.is_viewed = bool(first_view)
        p.viewed_at = first_view.viewed_at if first_view else None

        if p.year not in grouped:
            grouped[p.year] = []

        grouped[p.year].append(p)

    # CUD annuali del dipendente
    cuds = (
        Cud.objects
        .filter(employee=employee)
        .prefetch_related('cudview_set')
        .order_by('-year')
    )

    # Aggiunge info di visualizzazione CUD
    for c in cuds:
        first_view = c.cudview_set.order_by('viewed_at').first() if c.cudview_set.all() else None
        c.is_viewed = bool(first_view)
        c.viewed_at = first_view.viewed_at if first_view else None

        logger.info("about to render template")
    # --- Marcatura ---
    today = timezone.localdate()
    session, _ = WorkSession.objects.get_or_create(employee=employee, work_date=today)
    session.worked_display = session.worked_hours_display()
    active_assignments = _active_assignments_for_employee(employee, today)
    has_active_zone = bool(active_assignments)
    today_requests_qs = WorkMarkRequest.objects.filter(employee=employee, work_date=today).order_by('-created_at')
    today_mark_request_start = (
        today_requests_qs
        .filter(mark_type__in=[WorkMarkRequest.MARK_TYPE_START, WorkMarkRequest.MARK_TYPE_BOTH])
        .first()
    )
    today_mark_request_end = (
        today_requests_qs
        .filter(mark_type__in=[WorkMarkRequest.MARK_TYPE_END, WorkMarkRequest.MARK_TYPE_BOTH])
        .first()
    )
    # --- Fine Marcatura ---
    return render(request, 'portal/dashboard.html', {
        'employee': employee,
        'grouped_payslips': grouped,
        'cuds': cuds,
        'today_session': session,
        'has_active_zone': has_active_zone,
        'today_mark_request_start': today_mark_request_start,
        'today_mark_request_end': today_mark_request_end,
    })


@login_required
def dashboard(request):
    if user_has_full_admin_access(request.user):
        return redirect('admin_dashboard')
    if user_has_today_markings_access(request.user):
        return redirect('today_markings_dashboard')

    employee = Employee.objects.filter(user=request.user).first()
    if not employee:
        return HttpResponse("Profilo dipendente non trovato. Contatta l'amministratore.", status=403)

    today = timezone.localdate()
    month_start = today.replace(day=1)
    _sync_approved_requests_for_range(month_start, today, employee=employee)
    _reconcile_overnight_sessions(employee=employee, start_date=month_start, end_date=today)

    session, _ = _get_timekeeping_session(employee)
    session.worked_display = session.worked_hours_display()
    active_assignments = _active_assignments_for_employee(employee, today)
    has_active_zone = bool(active_assignments)
    active_zones = _active_zones_for_employee(employee, today)

    end_request_work_date = session.work_date if session.effective_started_at() and not session.effective_ended_at() else today
    start_requests_qs = WorkMarkRequest.objects.filter(employee=employee, work_date=today).order_by('-created_at')
    end_requests_qs = WorkMarkRequest.objects.filter(employee=employee, work_date=end_request_work_date).order_by('-created_at')
    today_mark_request_start = (
        start_requests_qs
        .filter(mark_type__in=[WorkMarkRequest.MARK_TYPE_START, WorkMarkRequest.MARK_TYPE_BOTH])
        .first()
    )
    today_mark_request_end = (
        end_requests_qs
        .filter(mark_type__in=[WorkMarkRequest.MARK_TYPE_END, WorkMarkRequest.MARK_TYPE_BOTH])
        .first()
    )
    request_status = request.GET.get('request_status', '')

    if request.method == 'POST' and request.POST.get('action') == 'request_out_of_zone':
        reason = (request.POST.get('reason') or '').strip()
        mark_type = (request.POST.get('mark_type') or '').strip()

        if mark_type not in {WorkMarkRequest.MARK_TYPE_START, WorkMarkRequest.MARK_TYPE_END}:
            return redirect(f"{request.path}?request_status=invalid_type")
        if len(reason) < 8:
            return redirect(f"{request.path}?request_status=invalid")

        target_work_date = end_request_work_date if mark_type == WorkMarkRequest.MARK_TYPE_END else today
        latest_request = (
            WorkMarkRequest.objects
            .filter(employee=employee, work_date=target_work_date, mark_type=mark_type)
            .order_by('-created_at')
            .first()
        )
        if latest_request and latest_request.status == WorkMarkRequest.STATUS_PENDING:
            return redirect(f"{request.path}?request_status=already_pending")

        request_obj = WorkMarkRequest.objects.create(
            employee=employee,
            work_date=target_work_date,
            mark_type=mark_type,
            reason=reason,
        )
        _send_out_of_zone_request_admin_notification(request_obj)

        _create_audit_event(
            request,
            'timekeeping_out_of_zone_requested',
            employee=employee,
            metadata={
                'work_date': str(target_work_date),
                'mark_type': mark_type,
                'reason': reason,
            },
                )
        return redirect(f"{request.path}?request_status=sent_{mark_type}")

    payslips = (
        Payslip.objects
        .filter(employee=employee)
        .prefetch_related('payslipview_set')
        .order_by('-year', '-month')
    )

    payslip_items = []
    for p in payslips:
        first_view = p.payslipview_set.order_by('viewed_at').first() if p.payslipview_set.all() else None
        p.is_viewed = bool(first_view)
        p.viewed_at = first_view.viewed_at if first_view else None
        payslip_items.append(_attach_payslip_display_period(p))

    payslip_items.sort(key=lambda item: (item.display_year, item.display_month, item.id), reverse=True)

    latest_payslip = payslip_items[0] if payslip_items else None
    grouped = {}
    for p in payslip_items:
        grouped.setdefault(p.display_year, []).append(p)

    cuds = (
        Cud.objects
        .filter(employee=employee)
        .prefetch_related('cudview_set')
        .order_by('-year')
    )
    for c in cuds:
        first_view = c.cudview_set.order_by('viewed_at').first() if c.cudview_set.all() else None
        c.is_viewed = bool(first_view)
        c.viewed_at = first_view.viewed_at if first_view else None

    month_sessions = (
        WorkSession.objects
        .filter(employee=employee, work_date__gte=month_start, work_date__lte=today)
        .order_by('-work_date')
    )
    month_sessions = list(month_sessions)
    for row in month_sessions:
        row.worked_display = row.worked_hours_display()
    month_total_minutes = sum(s.worked_minutes() for s in month_sessions)

    response = render(request, 'portal/dashboard.html', {
        'employee': employee,
        'grouped_payslips': grouped,
        'latest_payslip': latest_payslip,
        'cuds': cuds,
        'today_session': session,
        'has_active_zone': has_active_zone,
        'active_zones': active_zones,
        'today_mark_request_start': today_mark_request_start,
        'today_mark_request_end': today_mark_request_end,
        'request_status': request_status,
        'month_sessions': month_sessions[:15],
        'month_total_hours': f"{month_total_minutes // 60:02d}:{month_total_minutes % 60:02d}",
    })
    return _disable_response_cache(response)


def _haversine_meters(lat1, lon1, lat2, lon2):
    """Distanza geodetica approssimata in metri tra due coordinate."""
    earth_radius = 6371000
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius * c


def _parse_coordinate(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _active_assignments_for_employee(employee, on_date):
    assignments = (
        EmployeeWorkZone.objects
        .select_related("zone")
        .filter(
            employee=employee,
            is_active=True,
            zone__is_active=True,
            valid_from__lte=on_date,
        )
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=on_date))
    )
    return list(assignments)


def _active_zones_for_employee(employee, on_date):
    assignments = _active_assignments_for_employee(employee, on_date)
    return [a.zone for a in assignments]


def _evaluate_location_for_employee_zone(employee, lat, lon, on_date):
    assignments = _active_assignments_for_employee(employee, on_date)
    if not assignments or lat is None or lon is None:
        return {
            "assignment": None,
            "zone": None,
            "within": False,
            "distance_meters": None,
        }

    def distance_to_zone(z, plat, plon):
        # Ritorna (within_bool, distance_meters_to_perimeter)
        if getattr(z, 'shape', 'circle') == getattr(WorkZone, 'SHAPE_RECT', 'rect') and \
           z.rect_north is not None and z.rect_south is not None and z.rect_east is not None and z.rect_west is not None:
            n, s, e, w = float(z.rect_north), float(z.rect_south), float(z.rect_east), float(z.rect_west)
            within = (s <= plat <= n) and (w <= plon <= e)
            # distanza al rettangolo: 0 se dentro, altrimenti distanza al punto proiettato sul perimetro
            clamped_lat = min(max(plat, s), n)
            clamped_lon = min(max(plon, w), e)
            dist = 0.0 if within else _haversine_meters(plat, plon, clamped_lat, clamped_lon)
            return within, dist
        # default cerchio
        center_dist = _haversine_meters(plat, plon, float(z.latitude), float(z.longitude))
        within = center_dist <= float(z.radius_meters)
        dist = 0.0 if within else max(center_dist - float(z.radius_meters), 0.0)
        return within, dist

    best_assignment = None
    best_zone = None
    best_distance = None
    best_within = False

    for assignment in assignments:
        zone = assignment.zone
        within, dist = distance_to_zone(zone, lat, lon)
        # Scegli la zona piu vicina; preferisci "within" in caso di pari distanza
        if best_distance is None or dist < best_distance or (dist == best_distance and within and not best_within):
            best_distance = dist
            best_zone = zone
            best_assignment = assignment
            best_within = within

    return {
        "assignment": best_assignment,
        "zone": best_zone,
        "within": best_within,
        "distance_meters": round(best_distance, 1) if best_distance is not None else None,
    }


def _parse_time_or_none(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return None


def _session_has_markings(session):
    return bool(
        session.started_at
        or session.ended_at
        or session.corrected_started_at
        or session.corrected_ended_at
    )


def _clear_session_marking(session, delete_target):
    if delete_target == 'start':
        session.started_at = None
        session.corrected_started_at = None
        session.start_latitude = None
        session.start_longitude = None
        session.start_zone = None
        session.start_within_zone = False
        session.save(update_fields=[
            'started_at',
            'corrected_started_at',
            'start_latitude',
            'start_longitude',
            'start_zone',
            'start_within_zone',
            'updated_at',
        ])
        return

    if delete_target == 'end':
        session.ended_at = None
        session.corrected_ended_at = None
        session.end_latitude = None
        session.end_longitude = None
        session.end_zone = None
        session.end_within_zone = False
        session.save(update_fields=[
            'ended_at',
            'corrected_ended_at',
            'end_latitude',
            'end_longitude',
            'end_zone',
            'end_within_zone',
            'updated_at',
        ])
        return

    session.delete()


def _session_cell_text(session):
    if not session:
        return ''

    def fmt(dt):
        try:
            from django.utils import timezone as djtz
            if djtz.is_aware(dt):
                dt = djtz.localtime(dt)
        except Exception:
            pass
        return dt.strftime('%H:%M')

    start = session.effective_started_at()
    end = session.effective_ended_at()
    if start and end:
        return f"{fmt(start)}-{fmt(end)} ({session.worked_hours_display()})"
    if start:
        return f"IN {fmt(start)}"
    if end:
        return f"OUT {fmt(end)}"
    return ''


def _get_open_shift_session(employee, reference_ts=None):
    reference_ts = timezone.localtime(reference_ts or timezone.now())
    candidate_start_date = reference_ts.date() - timedelta(days=1)
    sessions = (
        WorkSession.objects
        .filter(employee=employee, work_date__gte=candidate_start_date)
        .select_related('start_zone', 'end_zone')
        .order_by('-work_date', '-created_at')
    )

    for session in sessions:
        start_dt = session.effective_started_at()
        end_dt = session.effective_ended_at()
        if not start_dt or end_dt:
            continue

        elapsed_hours = (reference_ts - start_dt).total_seconds() / 3600
        if 0 <= elapsed_hours <= MAX_SHIFT_DURATION_HOURS:
            return session

    return None


def _get_timekeeping_session(employee, reference_ts=None):
    reference_ts = timezone.localtime(reference_ts or timezone.now())
    open_session = _get_open_shift_session(employee, reference_ts)
    if open_session:
        return open_session, False
    return WorkSession.objects.get_or_create(employee=employee, work_date=reference_ts.date())


def _reconcile_overnight_sessions(employee=None, start_date=None, end_date=None):
    sessions_qs = WorkSession.objects.filter(
        Q(started_at__isnull=False)
        | Q(ended_at__isnull=False)
        | Q(corrected_started_at__isnull=False)
        | Q(corrected_ended_at__isnull=False)
    ).select_related('employee', 'end_zone')

    if employee is not None:
        sessions_qs = sessions_qs.filter(employee=employee)
    if start_date and end_date:
        sessions_qs = sessions_qs.filter(work_date__range=(start_date - timedelta(days=1), end_date))

    sessions = list(sessions_qs.order_by('employee_id', 'work_date', 'created_at'))
    previous_by_employee = {}

    for session in sessions:
        previous = previous_by_employee.get(session.employee_id)
        if not previous:
            previous_by_employee[session.employee_id] = session
            continue

        previous_start = previous.effective_started_at()
        previous_end = previous.effective_ended_at()
        current_start = session.effective_started_at()
        current_end = session.effective_ended_at()

        can_merge = (
            previous.work_date + timedelta(days=1) == session.work_date
            and previous_start is not None
            and previous_end is None
            and current_start is None
            and current_end is not None
        )

        if can_merge:
            elapsed_hours = (current_end - previous_start).total_seconds() / 3600
            if 0 <= elapsed_hours <= MAX_SHIFT_DURATION_HOURS:
                previous.ended_at = session.ended_at or previous.ended_at
                previous.corrected_ended_at = session.corrected_ended_at or previous.corrected_ended_at
                previous.end_latitude = session.end_latitude
                previous.end_longitude = session.end_longitude
                previous.end_zone = session.end_zone
                previous.end_within_zone = session.end_within_zone
                previous.correction_note = previous.correction_note or session.correction_note
                previous.corrected_by = previous.corrected_by or session.corrected_by
                previous.corrected_at = previous.corrected_at or session.corrected_at
                previous.save()

                session.delete()
                previous_by_employee[session.employee_id] = previous
                continue

        previous_by_employee[session.employee_id] = session


def _apply_approved_mark_request_to_session(request_obj):
    """Trasforma una richiesta fuori zona approvata in marcatura effettiva.

    Usa il timestamp della richiesta (created_at), non il momento dell'approvazione,
    per mantenere l'orario reale comunicato dal dipendente.
    """
    mark_ts = request_obj.created_at
    if request_obj.mark_type == WorkMarkRequest.MARK_TYPE_END:
        session = _get_open_shift_session(request_obj.employee, mark_ts)
        if session is None:
            session, _ = WorkSession.objects.get_or_create(
                employee=request_obj.employee,
                work_date=request_obj.work_date,
            )
    else:
        session, _ = WorkSession.objects.get_or_create(
            employee=request_obj.employee,
            work_date=request_obj.work_date,
        )

    changed_fields = []

    if request_obj.mark_type in {WorkMarkRequest.MARK_TYPE_START, WorkMarkRequest.MARK_TYPE_BOTH}:
        if not session.started_at:
            session.started_at = mark_ts
            session.start_within_zone = False
            changed_fields.extend(['started_at', 'start_within_zone'])

    if request_obj.mark_type in {WorkMarkRequest.MARK_TYPE_END, WorkMarkRequest.MARK_TYPE_BOTH}:
        if not session.ended_at:
            session.ended_at = mark_ts
            session.end_within_zone = False
            changed_fields.extend(['ended_at', 'end_within_zone'])

    if changed_fields:
        session.save(update_fields=changed_fields + ['updated_at'])

    return session


def _sync_approved_requests_for_range(start_date, end_date, employee=None):
    """Allinea WorkSession con richieste approvate gia esistenti nel range date."""
    qs = (
        WorkMarkRequest.objects
        .select_related('employee')
        .filter(
            status=WorkMarkRequest.STATUS_APPROVED,
            work_date__range=(start_date, end_date),
        )
        .order_by('work_date', 'created_at')
    )
    if employee is not None:
        qs = qs.filter(employee=employee)

    for req in qs:
        _apply_approved_mark_request_to_session(req)


@login_required
def timekeeping(request):
    """Marcatura dipendente: avvio/fine giornata con supporto geolocalizzazione."""
    if user_has_full_admin_access(request.user):
        return redirect('admin_timekeeping')
    if user_has_today_markings_access(request.user):
        return redirect('today_markings_dashboard')

    employee = get_object_or_404(Employee, user=request.user)
    today = timezone.localdate()
    month_start = today.replace(day=1)

    # Rende visibili immediatamente nel riepilogo le richieste gia approvate.
    _sync_approved_requests_for_range(month_start, today, employee=employee)
    _reconcile_overnight_sessions(employee=employee, start_date=month_start, end_date=today)

    session, _ = _get_timekeeping_session(employee)
    session.worked_display = session.worked_hours_display()
    active_assignments = _active_assignments_for_employee(employee, today)
    has_active_zone = bool(active_assignments)
    end_request_work_date = session.work_date if session.effective_started_at() and not session.effective_ended_at() else today
    start_requests_qs = WorkMarkRequest.objects.filter(employee=employee, work_date=today).order_by('-created_at')
    end_requests_qs = WorkMarkRequest.objects.filter(employee=employee, work_date=end_request_work_date).order_by('-created_at')

    today_mark_request_start = (
        start_requests_qs
        .filter(mark_type__in=[WorkMarkRequest.MARK_TYPE_START, WorkMarkRequest.MARK_TYPE_BOTH])
        .first()
    )
    today_mark_request_end = (
        end_requests_qs
        .filter(mark_type__in=[WorkMarkRequest.MARK_TYPE_END, WorkMarkRequest.MARK_TYPE_BOTH])
        .first()
    )
    request_status = request.GET.get('request_status', '')

    def has_approved_request_for_action(action_name):
        mark_types = [WorkMarkRequest.MARK_TYPE_BOTH]
        target_work_date = today
        if action_name == 'start':
            mark_types.append(WorkMarkRequest.MARK_TYPE_START)
        if action_name == 'end':
            mark_types.append(WorkMarkRequest.MARK_TYPE_END)
            target_work_date = end_request_work_date
        return WorkMarkRequest.objects.filter(
            employee=employee,
            work_date=target_work_date,
            status=WorkMarkRequest.STATUS_APPROVED,
            mark_type__in=mark_types,
        ).exists()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'request_out_of_zone':
            reason = (request.POST.get('reason') or '').strip()
            mark_type = (request.POST.get('mark_type') or '').strip()
            if mark_type not in {WorkMarkRequest.MARK_TYPE_START, WorkMarkRequest.MARK_TYPE_END}:
                return redirect(f"{request.path}?request_status=invalid_type")
            if len(reason) < 8:
                return redirect(f"{request.path}?request_status=invalid")

            target_work_date = end_request_work_date if mark_type == WorkMarkRequest.MARK_TYPE_END else today

            latest_request = (
                WorkMarkRequest.objects
                .filter(employee=employee, work_date=target_work_date, mark_type=mark_type)
                .order_by('-created_at')
                .first()
            )

            if latest_request and latest_request.status == WorkMarkRequest.STATUS_PENDING:
                return redirect(f"{request.path}?request_status=already_pending")

            request_obj = WorkMarkRequest.objects.create(
                employee=employee,
                work_date=target_work_date,
                mark_type=mark_type,
                reason=reason,
            )
            _send_out_of_zone_request_admin_notification(request_obj)

            _create_audit_event(
                request,
                'timekeeping_out_of_zone_requested',
                employee=employee,
                metadata={
                    'work_date': str(target_work_date),
                    'mark_type': mark_type,
                    'reason': reason,
                },
            )
            return redirect(f"{request.path}?request_status=sent_{mark_type}")

        latitude = _parse_coordinate(request.POST.get('latitude'))
        longitude = _parse_coordinate(request.POST.get('longitude'))

        if not has_active_zone:
            return JsonResponse(
                {'ok': False, 'error': 'Marcatura non disponibile: nessuna zona attiva assegnata.'},
                status=400,
            )

        if action not in {'start', 'end'}:
            return JsonResponse({'ok': False, 'error': 'Azione non valida.'}, status=400)

        approved_out_of_zone = has_approved_request_for_action(action)

        if action == 'start' and session.effective_started_at() and not session.effective_ended_at():
            return JsonResponse({'ok': False, 'error': 'Hai gia un turno aperto. Completa prima l\'uscita.'}, status=400)

        if action == 'end' and not session.effective_started_at():
            return JsonResponse({'ok': False, 'error': 'Devi marcare prima l\'ingresso.'}, status=400)

        if action == 'end' and session.effective_ended_at():
            return JsonResponse({'ok': False, 'error': 'Uscita gia marcata oggi.'}, status=400)

        now_ts = timezone.now()
        zone_check = _evaluate_location_for_employee_zone(employee, latitude, longitude, today)
        strict_mode = any(a.strict_geofence for a in active_assignments)

        if strict_mode and (latitude is None or longitude is None) and not approved_out_of_zone:
            return JsonResponse(
                {'ok': False, 'error': 'Geolocalizzazione obbligatoria: attiva il GPS per marcare.'},
                status=400,
            )

        if strict_mode and active_assignments and not zone_check['within'] and not approved_out_of_zone:
            return JsonResponse(
                {'ok': False, 'error': 'Marcatura bloccata: sei fuori dalla zona assegnata.'},
                status=400,
            )

        if action == 'start':
            session.started_at = now_ts
            session.start_latitude = latitude
            session.start_longitude = longitude
            session.start_zone = zone_check['zone']
            session.start_within_zone = zone_check['within']
            session.save()

            _create_audit_event(
                request,
                'timekeeping_start',
                employee=employee,
                metadata={
                    'work_date': str(today),
                    'zone': zone_check['zone'].name if zone_check['zone'] else None,
                    'within_zone': zone_check['within'],
                    'distance_meters': zone_check['distance_meters'],
                },
            )

        if action == 'end':
            session.ended_at = now_ts
            session.end_latitude = latitude
            session.end_longitude = longitude
            session.end_zone = zone_check['zone']
            session.end_within_zone = zone_check['within']
            session.save()

            _create_audit_event(
                request,
                'timekeeping_end',
                employee=employee,
                metadata={
                    'work_date': str(today),
                    'zone': zone_check['zone'].name if zone_check['zone'] else None,
                    'within_zone': zone_check['within'],
                    'distance_meters': zone_check['distance_meters'],
                    'worked_minutes': session.worked_minutes(),
                },
            )

        return JsonResponse({
            'ok': True,
            'action': action,
            'started_at': session.started_at.strftime('%H:%M') if session.started_at else None,
            'ended_at': session.ended_at.strftime('%H:%M') if session.ended_at else None,
            'worked': session.worked_hours_display(),
            'zone': zone_check['zone'].name if zone_check['zone'] else None,
            'within_zone': zone_check['within'],
            'distance_meters': zone_check['distance_meters'],
        })

    month_sessions = (
        WorkSession.objects
        .filter(employee=employee, work_date__gte=month_start, work_date__lte=today)
        .order_by('-work_date')
    )
    month_sessions = list(month_sessions)
    for row in month_sessions:
        row.worked_display = row.worked_hours_display()
    month_total_minutes = sum(s.worked_minutes() for s in month_sessions)

    response = render(request, 'portal/timekeeping.html', {
        'employee': employee,
        'today_session': session,
        'active_zones': _active_zones_for_employee(employee, today),
        'has_active_zone': has_active_zone,
        'today_mark_request_start': today_mark_request_start,
        'today_mark_request_end': today_mark_request_end,
        'request_status': request_status,
        'month_sessions': month_sessions[:15],
        'month_total_hours': f"{month_total_minutes // 60:02d}:{month_total_minutes % 60:02d}",
    })
    return _disable_response_cache(response)


@login_required
def admin_timekeeping(request):
    """Report mensile marcature con dettaglio giornaliero per dipendente."""
    if not request.user.is_staff:
        return redirect('dashboard')

    today = timezone.localdate()
    feedback = None
    feedback_level = 'info'

    if request.method == 'POST':
        action = request.POST.get('action')

        if action in {'approve_mark_request', 'reject_mark_request'}:
            req_id = request.POST.get('request_id')
            request_obj = WorkMarkRequest.objects.filter(id=req_id).select_related('employee').first()
            if request_obj:
                request_obj.status = (
                    WorkMarkRequest.STATUS_APPROVED
                    if action == 'approve_mark_request'
                    else WorkMarkRequest.STATUS_REJECTED
                )
                request_obj.review_note = (request.POST.get('review_note') or '').strip() or None
                request_obj.reviewed_by = request.user
                request_obj.reviewed_at = timezone.now()
                request_obj.save(update_fields=['status', 'review_note', 'reviewed_by', 'reviewed_at', 'updated_at'])

                if request_obj.status == WorkMarkRequest.STATUS_APPROVED:
                    _apply_approved_mark_request_to_session(request_obj)

                _create_audit_event(
                    request,
                    'timekeeping_out_of_zone_reviewed',
                    employee=request_obj.employee,
                    metadata={
                        'request_id': request_obj.id,
                        'work_date': str(request_obj.work_date),
                        'status': request_obj.status,
                        'mark_type': request_obj.mark_type,
                        'marked_at': request_obj.created_at.isoformat() if request_obj.status == WorkMarkRequest.STATUS_APPROVED else None,
                    },
                )

            return redirect(request.get_full_path() or request.path)

        if action == 'correct_day':
            employee_id = request.POST.get('employee_id')
            target_date_raw = request.POST.get('target_date')
            start_time = _parse_time_or_none(request.POST.get('start_time'))
            end_time = _parse_time_or_none(request.POST.get('end_time'))
            note = (request.POST.get('note') or '').strip()

            employee = Employee.objects.filter(id=employee_id).first()
            try:
                target_date = datetime.strptime(target_date_raw or '', '%Y-%m-%d').date()
            except ValueError:
                target_date = None

            if employee and target_date:
                session, _ = WorkSession.objects.get_or_create(employee=employee, work_date=target_date)
                reference_start_dt = session.corrected_started_at or session.started_at

                if start_time:
                    corrected_start = datetime.combine(target_date, start_time)
                    session.corrected_started_at = timezone.make_aware(corrected_start, timezone.get_current_timezone())
                    reference_start_dt = session.corrected_started_at
                else:
                    session.corrected_started_at = None
                    reference_start_dt = session.started_at

                if end_time:
                    end_date_for_correction = target_date
                    if reference_start_dt and end_time <= reference_start_dt.timetz().replace(tzinfo=None):
                        end_date_for_correction = target_date + timedelta(days=1)
                    corrected_end = datetime.combine(end_date_for_correction, end_time)
                    session.corrected_ended_at = timezone.make_aware(corrected_end, timezone.get_current_timezone())
                else:
                    session.corrected_ended_at = None

                session.correction_note = note or None
                session.corrected_by = request.user
                session.corrected_at = timezone.now()
                session.save()

                _create_audit_event(
                    request,
                    'timekeeping_corrected',
                    employee=employee,
                    metadata={
                        'work_date': str(target_date),
                        'corrected_started_at': session.corrected_started_at.isoformat() if session.corrected_started_at else None,
                        'corrected_ended_at': session.corrected_ended_at.isoformat() if session.corrected_ended_at else None,
                        'note': session.correction_note,
                    },
                )

                return redirect(
                    f"{request.path}?employee={employee.id}&month={target_date.month}&year={target_date.year}"
                )

        if action == 'delete_marking':
            employee_id = request.POST.get('employee_id')
            target_date_raw = request.POST.get('target_date')
            delete_target = (request.POST.get('delete_target') or '').strip()

            employee = Employee.objects.filter(id=employee_id).first()
            try:
                target_date = datetime.strptime(target_date_raw or '', '%Y-%m-%d').date()
            except ValueError:
                target_date = None

            redirect_employee = request.POST.get('redirect_employee') or 'all'
            redirect_month = request.POST.get('redirect_month') or str(today.month)
            redirect_year = request.POST.get('redirect_year') or str(today.year)

            redirect_url = f"{request.path}?employee={redirect_employee}&month={redirect_month}&year={redirect_year}"

            if not employee or not target_date or delete_target not in {'start', 'end', 'day'}:
                return redirect(f"{redirect_url}&outcome=delete_invalid")

            session = WorkSession.objects.filter(employee=employee, work_date=target_date).first()
            if not session:
                return redirect(f"{redirect_url}&outcome=delete_missing")

            payload = {
                'work_date': str(target_date),
                'delete_target': delete_target,
                'started_at': session.started_at.isoformat() if session.started_at else None,
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                'corrected_started_at': session.corrected_started_at.isoformat() if session.corrected_started_at else None,
                'corrected_ended_at': session.corrected_ended_at.isoformat() if session.corrected_ended_at else None,
            }

            request_types = []
            if delete_target in {'start', 'day'}:
                request_types.extend([WorkMarkRequest.MARK_TYPE_START, WorkMarkRequest.MARK_TYPE_BOTH])
            if delete_target in {'end', 'day'}:
                request_types.extend([WorkMarkRequest.MARK_TYPE_END, WorkMarkRequest.MARK_TYPE_BOTH])

            related_requests = list(
                WorkMarkRequest.objects
                .filter(
                    employee=employee,
                    work_date=target_date,
                    mark_type__in=request_types,
                    status__in=[WorkMarkRequest.STATUS_APPROVED, WorkMarkRequest.STATUS_PENDING],
                )
                .order_by('-created_at')
            )

            payload['related_request_ids'] = [req.id for req in related_requests]
            payload['related_request_statuses'] = [req.status for req in related_requests]

            _clear_session_marking(session, delete_target)

            if related_requests:
                WorkMarkRequest.objects.filter(id__in=[req.id for req in related_requests]).delete()

            if delete_target != 'day' and not _session_has_markings(session):
                session.delete()

            _create_audit_event(
                request,
                'timekeeping_marking_deleted',
                employee=employee,
                metadata=payload,
            )

            return redirect(f"{redirect_url}&outcome=deleted_{delete_target}")

    try:
        year = int(request.GET.get('year', today.year))
    except (TypeError, ValueError):
        year = today.year

    try:
        month = int(request.GET.get('month', today.month))
    except (TypeError, ValueError):
        month = today.month

    month = max(1, min(month, 12))

    outcome = (request.GET.get('outcome') or '').strip()
    if outcome == 'deleted_start':
        feedback = 'Marcatura di ingresso eliminata.'
        feedback_level = 'warning'
    elif outcome == 'deleted_end':
        feedback = 'Marcatura di uscita eliminata.'
        feedback_level = 'warning'
    elif outcome == 'deleted_day':
        feedback = 'Giornata di marcatura eliminata.'
        feedback_level = 'warning'
    elif outcome == 'delete_missing':
        feedback = 'Marcatura non trovata o gia eliminata.'
        feedback_level = 'danger'
    elif outcome == 'delete_invalid':
        feedback = 'Richiesta di cancellazione non valida.'
        feedback_level = 'danger'

    employees = Employee.objects.order_by('last_name', 'first_name')

    month_choices = [
        (1, 'Gennaio'),
        (2, 'Febbraio'),
        (3, 'Marzo'),
        (4, 'Aprile'),
        (5, 'Maggio'),
        (6, 'Giugno'),
        (7, 'Luglio'),
        (8, 'Agosto'),
        (9, 'Settembre'),
        (10, 'Ottobre'),
        (11, 'Novembre'),
        (12, 'Dicembre'),
    ]

    employee_filter = (request.GET.get('employee') or 'all').strip()
    all_mode = employee_filter == 'all'

    selected_employee = None
    if not all_mode:
        if employee_filter:
            selected_employee = employees.filter(id=employee_filter).first()

    rows = []
    total_minutes = 0
    incomplete_days = 0

    month_last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, month_last_day)

    pending_mark_requests = (
        WorkMarkRequest.objects
        .select_related('employee')
        .filter(status=WorkMarkRequest.STATUS_PENDING)
        .order_by('-created_at')[:20]
    )

    # Backfill in lettura: include nel report mensile eventuali approvazioni storiche.
    if all_mode:
        _sync_approved_requests_for_range(start_date, end_date)
        _reconcile_overnight_sessions(start_date=start_date, end_date=end_date)
    elif selected_employee:
        _sync_approved_requests_for_range(start_date, end_date, employee=selected_employee)
        _reconcile_overnight_sessions(employee=selected_employee, start_date=start_date, end_date=end_date)

    if all_mode:
        marked_sessions_qs = (
            WorkSession.objects
            .filter(work_date__range=(start_date, end_date))
            .filter(
                Q(started_at__isnull=False)
                | Q(ended_at__isnull=False)
                | Q(corrected_started_at__isnull=False)
                | Q(corrected_ended_at__isnull=False)
            )
            .select_related('employee')
            .order_by('employee__last_name', 'employee__first_name', 'work_date')
        )

        sessions_by_employee_day = {}
        employee_ids = []
        seen_ids = set()
        for s in marked_sessions_qs:
            if s.employee_id not in seen_ids:
                seen_ids.add(s.employee_id)
                employee_ids.append(s.employee_id)
            sessions_by_employee_day[(s.employee_id, s.work_date.day)] = s

        if employee_ids:
            matrix_employees = list(
                Employee.objects
                .filter(id__in=employee_ids)
                .order_by('last_name', 'first_name')
            )
        else:
            matrix_employees = []

        day_numbers = list(range(1, month_last_day + 1))
        matrix_rows = []
        for emp in matrix_employees:
            cells = []
            employee_total_minutes = 0
            for day_number in day_numbers:
                session = sessions_by_employee_day.get((emp.id, day_number))
                if session:
                    employee_total_minutes += session.worked_minutes()
                cells.append({
                    'day': day_number,
                    'value': _session_cell_text(session),
                })
            matrix_rows.append({
                'employee': emp,
                'cells': cells,
                'month_total': f"{employee_total_minutes // 60:02d}:{employee_total_minutes % 60:02d}",
            })

        export_format = request.GET.get('format')
        if export_format == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="report_marcature_tutti_{year}_{month}.csv"'
            response.write('\ufeff')
            writer = csv.writer(response, delimiter=';')
            day_headers = [date(year, month, d).strftime('%d/%m/%Y') for d in day_numbers]
            writer.writerow(['Dipendente'] + day_headers + ['Totale ore lavorate'])
            for row in matrix_rows:
                writer.writerow(
                    [row['employee'].full_name]
                    + [cell['value'] for cell in row['cells']]
                    + [row['month_total']]
                )
            return response

        return render(request, 'portal/admin_timekeeping.html', {
            'employees': employees,
            'month_choices': month_choices,
            'selected_employee': None,
            'selected_year': year,
            'selected_month': month,
            'rows': [],
            'month_total': '00:00',
            'incomplete_days': 0,
            'all_mode': True,
            'day_numbers': day_numbers,
            'matrix_rows': matrix_rows,
            'employee_filter': 'all',
            'pending_mark_requests': pending_mark_requests,
            'feedback': feedback,
            'feedback_level': feedback_level,
        })

    if selected_employee:
        sessions = (
            WorkSession.objects
            .filter(employee=selected_employee, work_date__range=(start_date, end_date))
            .select_related('start_zone', 'end_zone', 'corrected_by')
            .order_by('work_date')
        )
        by_day = {s.work_date: s for s in sessions}

        export_format = request.GET.get('format')
        if export_format == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="marcature_{selected_employee.id}_{year}_{month}.csv"'
            response.write('\ufeff')
            writer = csv.writer(response, delimiter=';')
            writer.writerow([
                'Data',
                'Ingresso',
                'Uscita',
                'Totale',
                'Zona ingresso',
                'Zona uscita',
                'In zona ingresso',
                'In zona uscita',
                'Corretto da admin',
                'Nota correzione',
            ])

            for day in range(1, month_last_day + 1):
                current_date = date(year, month, day)
                session = by_day.get(current_date)
                if not session:
                    writer.writerow([current_date.strftime('%d/%m/%Y'), '', '', '00:00', '', '', '', '', '', ''])
                    continue
                writer.writerow([
                    current_date.strftime('%d/%m/%Y'),
                    session.effective_started_at().strftime('%H:%M') if session.effective_started_at() else '',
                    session.effective_ended_at().strftime('%H:%M') if session.effective_ended_at() else '',
                    session.worked_hours_display(),
                    session.start_zone.name if session.start_zone else '',
                    session.end_zone.name if session.end_zone else '',
                    'si' if session.start_within_zone else 'no',
                    'si' if session.end_within_zone else 'no',
                    'si' if session.corrected_at else 'no',
                    session.correction_note or '',
                ])
            return response

        if export_format == 'xlsx':
            from openpyxl import Workbook
            from openpyxl.styles import Font

            wb = Workbook()
            ws = wb.active
            ws.title = 'Marcature'

            headers = [
                'Data',
                'Ingresso',
                'Uscita',
                'Totale',
                'Zona ingresso',
                'Zona uscita',
                'In zona ingresso',
                'In zona uscita',
                'Corretto da admin',
                'Nota correzione',
            ]
            ws.append(headers)
            for cell in ws[1]:
                cell.font = Font(bold=True)

            total_month_minutes = 0
            for day in range(1, month_last_day + 1):
                current_date = date(year, month, day)
                session = by_day.get(current_date)
                if not session:
                    ws.append([current_date.strftime('%d/%m/%Y'), '', '', '00:00', '', '', '', '', '', ''])
                    continue

                minutes = session.worked_minutes()
                total_month_minutes += minutes
                ws.append([
                    current_date.strftime('%d/%m/%Y'),
                    session.effective_started_at().strftime('%H:%M') if session.effective_started_at() else '',
                    session.effective_ended_at().strftime('%H:%M') if session.effective_ended_at() else '',
                    session.worked_hours_display(),
                    session.start_zone.name if session.start_zone else '',
                    session.end_zone.name if session.end_zone else '',
                    'si' if session.start_within_zone else 'no',
                    'si' if session.end_within_zone else 'no',
                    'si' if session.corrected_at else 'no',
                    session.correction_note or '',
                ])

            summary_row = month_last_day + 3
            ws.cell(row=summary_row, column=1, value='Totale mese')
            ws.cell(
                row=summary_row,
                column=4,
                value=f"{total_month_minutes // 60:02d}:{total_month_minutes % 60:02d}",
            )
            ws.cell(row=summary_row, column=1).font = Font(bold=True)
            ws.cell(row=summary_row, column=4).font = Font(bold=True)

            # Larghezze minime utili per una lettura immediata del file.
            for idx, width in {
                1: 12,
                2: 10,
                3: 10,
                4: 10,
                5: 22,
                6: 22,
                7: 14,
                8: 14,
                9: 16,
                10: 30,
            }.items():
                ws.column_dimensions[chr(64 + idx)].width = width

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = (
                f'attachment; filename="marcature_{selected_employee.id}_{year}_{month}.xlsx"'
            )
            wb.save(response)
            return response

        for day in range(1, month_last_day + 1):
            current_date = date(year, month, day)
            session = by_day.get(current_date)

            if not session:
                rows.append({
                    'date': current_date,
                    'entry': None,
                    'exit': None,
                    'total': '00:00',
                    'status': 'missing',
                    'start_zone': None,
                    'end_zone': None,
                })
                continue

            worked = session.worked_minutes()
            total_minutes += worked
            effective_start = session.effective_started_at()
            effective_end = session.effective_ended_at()
            if effective_start and not effective_end:
                incomplete_days += 1

            rows.append({
                'date': current_date,
                'entry': effective_start,
                'exit': effective_end,
                'total': session.worked_hours_display(),
                'status': 'ok' if effective_start and effective_end else 'partial',
                'start_zone': session.start_zone,
                'end_zone': session.end_zone,
                'start_within_zone': session.start_within_zone,
                'end_within_zone': session.end_within_zone,
                'corrected': bool(session.corrected_at),
                'correction_note': session.correction_note,
            })

    return render(request, 'portal/admin_timekeeping.html', {
        'employees': employees,
        'month_choices': month_choices,
        'selected_employee': selected_employee,
        'selected_year': year,
        'selected_month': month,
        'rows': rows,
        'month_total': f"{total_minutes // 60:02d}:{total_minutes % 60:02d}",
        'incomplete_days': incomplete_days,
        'all_mode': False,
        'day_numbers': [],
        'matrix_rows': [],
        'employee_filter': str(selected_employee.id) if selected_employee else '',
        'pending_mark_requests': pending_mark_requests,
        'feedback': feedback,
        'feedback_level': feedback_level,
    })


@login_required
def admin_out_of_zone_requests(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    feedback = None
    feedback_level = 'info'

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete_out_of_zone_request':
            req_id = request.POST.get('request_id')
            redirect_query = (request.POST.get('redirect_query') or '').strip()
            request_obj = (
                WorkMarkRequest.objects
                .select_related('employee', 'reviewed_by')
                .filter(id=req_id)
                .first()
            )

            if request_obj:
                employee = request_obj.employee
                request_payload = {
                    'request_id': request_obj.id,
                    'work_date': str(request_obj.work_date),
                    'status': request_obj.status,
                    'mark_type': request_obj.mark_type,
                    'reason': request_obj.reason,
                    'review_note': request_obj.review_note,
                    'reviewed_at': request_obj.reviewed_at.isoformat() if request_obj.reviewed_at else None,
                    'reviewed_by': request_obj.reviewed_by.username if request_obj.reviewed_by else None,
                }
                request_obj.delete()

                _create_audit_event(
                    request,
                    'timekeeping_out_of_zone_deleted',
                    employee=employee,
                    metadata=request_payload,
                )

                redirect_url = request.path
                if redirect_query:
                    redirect_url = f'{redirect_url}?{redirect_query}&outcome=deleted'
                else:
                    redirect_url = f'{redirect_url}?outcome=deleted'
                return redirect(redirect_url)

            redirect_url = request.path
            if redirect_query:
                redirect_url = f'{redirect_url}?{redirect_query}&outcome=missing'
            else:
                redirect_url = f'{redirect_url}?outcome=missing'
            return redirect(redirect_url)

    outcome = (request.GET.get('outcome') or '').strip()
    if outcome == 'deleted':
        feedback = 'Richiesta fuori zona eliminata definitivamente.'
        feedback_level = 'warning'
    elif outcome == 'missing':
        feedback = 'Richiesta non trovata o gia eliminata.'
        feedback_level = 'danger'

    employees = Employee.objects.order_by('last_name', 'first_name')
    history_status = (request.GET.get('status') or 'all').strip()
    if history_status not in {
        'all',
        WorkMarkRequest.STATUS_PENDING,
        WorkMarkRequest.STATUS_APPROVED,
        WorkMarkRequest.STATUS_REJECTED,
    }:
        history_status = 'all'

    history_employee_filter = (request.GET.get('employee') or 'all').strip()
    history_requests_qs = (
        WorkMarkRequest.objects
        .select_related('employee', 'reviewed_by')
        .order_by('-created_at')
    )
    if history_status != 'all':
        history_requests_qs = history_requests_qs.filter(status=history_status)
    if history_employee_filter != 'all':
        history_requests_qs = history_requests_qs.filter(employee_id=history_employee_filter)

    history_requests_page = Paginator(history_requests_qs, 25).get_page(request.GET.get('page') or 1)
    pending_requests_count = WorkMarkRequest.objects.filter(status=WorkMarkRequest.STATUS_PENDING).count()

    return render(request, 'portal/admin_out_of_zone_requests.html', {
        'employees': employees,
        'history_requests_page': history_requests_page,
        'history_status': history_status,
        'history_employee_filter': history_employee_filter,
        'pending_requests_count': pending_requests_count,
        'feedback': feedback,
        'feedback_level': feedback_level,
        'current_query_string': request.GET.urlencode,
    })


@login_required
def admin_work_zones(request):
    """Configurazione zone di lavoro e assegnazioni dipendente-zona."""
    if not request.user.is_staff:
        return redirect('dashboard')

    feedback = None
    feedback_level = 'info'

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_zone':
            name = (request.POST.get('name') or '').strip()
            shape = (request.POST.get('shape') or 'circle').strip()

            if shape == 'rect':
                n = _parse_coordinate(request.POST.get('rect_north'))
                s = _parse_coordinate(request.POST.get('rect_south'))
                e = _parse_coordinate(request.POST.get('rect_east'))
                w = _parse_coordinate(request.POST.get('rect_west'))
                if not name or None in (n, s, e, w) or not (n > s and e > w):
                    feedback = 'Rettangolo non valido. Inserisci Nord>Sud ed Est>Ovest.'
                    feedback_level = 'danger'
                else:
                    # Centro per compatibilita con viste esistenti
                    center_lat = (float(n) + float(s)) / 2.0
                    center_lon = (float(e) + float(w)) / 2.0
                    WorkZone.objects.create(
                        name=name,
                        shape=WorkZone.SHAPE_RECT,
                        latitude=center_lat,
                        longitude=center_lon,
                        radius_meters=100,
                        rect_north=n,
                        rect_south=s,
                        rect_east=e,
                        rect_west=w,
                    )
                    feedback = 'Zona rettangolare creata correttamente.'
                    feedback_level = 'success'
            else:
                radius_raw = request.POST.get('radius_meters') or '100'
                latitude = _parse_coordinate(request.POST.get('latitude'))
                longitude = _parse_coordinate(request.POST.get('longitude'))
                try:
                    radius = max(int(radius_raw), 10)
                except (TypeError, ValueError):
                    radius = 100

                if not name or latitude is None or longitude is None:
                    feedback = 'Compila nome e coordinate valide per creare la zona.'
                    feedback_level = 'danger'
                else:
                    WorkZone.objects.create(
                        name=name,
                        shape=WorkZone.SHAPE_CIRCLE,
                        latitude=latitude,
                        longitude=longitude,
                        radius_meters=radius,
                        rect_north=None,
                        rect_south=None,
                        rect_east=None,
                        rect_west=None,
                    )
                    feedback = 'Zona circolare creata correttamente.'
                    feedback_level = 'success'

        if action == 'update_zone':
            zone_id = request.POST.get('zone_id')
            zone = WorkZone.objects.filter(id=zone_id).first()
            if not zone:
                feedback = 'Zona non trovata.'
                feedback_level = 'danger'
            else:
                name = (request.POST.get('name') or '').strip()
                shape = (request.POST.get('shape') or 'circle').strip()
                if not name:
                    feedback = 'Inserisci un nome valido.'
                    feedback_level = 'danger'
                else:
                    zone.name = name
                    if shape == 'rect':
                        n = _parse_coordinate(request.POST.get('rect_north'))
                        s = _parse_coordinate(request.POST.get('rect_south'))
                        e = _parse_coordinate(request.POST.get('rect_east'))
                        w = _parse_coordinate(request.POST.get('rect_west'))
                        if None in (n, s, e, w) or not (n > s and e > w):
                            feedback = 'Rettangolo non valido. Inserisci Nord>Sud ed Est>Ovest.'
                            feedback_level = 'danger'
                        else:
                            center_lat = (float(n) + float(s)) / 2.0
                            center_lon = (float(e) + float(w)) / 2.0
                            zone.shape = WorkZone.SHAPE_RECT
                            zone.latitude = center_lat
                            zone.longitude = center_lon
                            zone.rect_north = n
                            zone.rect_south = s
                            zone.rect_east = e
                            zone.rect_west = w
                            # mantieni radius invariato ma irrilevante
                            zone.save()
                            feedback = 'Zona aggiornata (rettangolo).'
                            feedback_level = 'success'
                    else:
                        latitude = _parse_coordinate(request.POST.get('latitude'))
                        longitude = _parse_coordinate(request.POST.get('longitude'))
                        radius_raw = request.POST.get('radius_meters') or '100'
                        try:
                            radius = max(int(radius_raw), 10)
                        except (TypeError, ValueError):
                            radius = 100
                        if latitude is None or longitude is None:
                            feedback = 'Coordinate non valide.'
                            feedback_level = 'danger'
                        else:
                            zone.shape = WorkZone.SHAPE_CIRCLE
                            zone.latitude = latitude
                            zone.longitude = longitude
                            zone.radius_meters = radius
                            zone.rect_north = None
                            zone.rect_south = None
                            zone.rect_east = None
                            zone.rect_west = None
                            zone.save()
                            feedback = 'Zona aggiornata (cerchio).'
                            feedback_level = 'success'

        if action == 'assign_zone':
            employee_id = request.POST.get('employee_id')
            zone_id = request.POST.get('zone_id')
            valid_from = request.POST.get('valid_from')
            strict_geofence = request.POST.get('strict_geofence') == '1'

            employee = Employee.objects.filter(id=employee_id).first()
            zone = WorkZone.objects.filter(id=zone_id, is_active=True).first()

            if not employee or not zone:
                feedback = 'Seleziona dipendente e zona validi.'
                feedback_level = 'danger'
            else:
                try:
                    EmployeeWorkZone.objects.create(
                        employee=employee,
                        zone=zone,
                        valid_from=valid_from or timezone.localdate(),
                        strict_geofence=strict_geofence,
                    )
                    feedback = 'Zona assegnata al dipendente.'
                    feedback_level = 'success'
                except IntegrityError:
                    feedback = 'Assegnazione gia presente con la stessa data di validita.'
                    feedback_level = 'warning'

        if action == 'deactivate_assignment':
            assignment_id = request.POST.get('assignment_id')
            assignment = EmployeeWorkZone.objects.filter(id=assignment_id).first()

            if not assignment:
                feedback = 'Assegnazione non trovata.'
                feedback_level = 'danger'
            else:
                assignment.is_active = False
                assignment.valid_to = assignment.valid_to or timezone.localdate()
                assignment.save(update_fields=['is_active', 'valid_to'])
                feedback = 'Assegnazione disattivata.'
                feedback_level = 'warning'

        if action == 'delete_zone':
            zone_id = request.POST.get('zone_id')
            zone = WorkZone.objects.filter(id=zone_id).first()

            if not zone:
                feedback = 'Zona non trovata.'
                feedback_level = 'danger'
            else:
                zone_name = zone.name
                zone.delete()
                feedback = f'Zona "{zone_name}" eliminata.'
                feedback_level = 'warning'

        if action == 'delete_assignment':
            assignment_id = request.POST.get('assignment_id')
            assignment = EmployeeWorkZone.objects.select_related('employee', 'zone').filter(id=assignment_id).first()

            if not assignment:
                feedback = 'Assegnazione non trovata.'
                feedback_level = 'danger'
            else:
                employee_name = assignment.employee.full_name
                zone_name = assignment.zone.name
                assignment.delete()
                feedback = f'Assegnazione eliminata: {employee_name} -> {zone_name}.'
                feedback_level = 'warning'

    employees = Employee.objects.order_by('last_name', 'first_name')
    zones = WorkZone.objects.order_by('name')
    assignments = (
        EmployeeWorkZone.objects
        .select_related('employee', 'zone')
        .order_by('employee__last_name', 'employee__first_name', '-is_active', 'zone__name', '-created_at')
    )
    assignment_groups_map = OrderedDict()

    for assignment in assignments:
        employee_id = assignment.employee_id
        group = assignment_groups_map.get(employee_id)
        if group is None:
            group = {
                'employee': assignment.employee,
                'assignments': [],
                'total_count': 0,
                'active_count': 0,
            }
            assignment_groups_map[employee_id] = group

        group['assignments'].append(assignment)
        group['total_count'] += 1
        if assignment.is_active:
            group['active_count'] += 1

    assignment_groups = list(assignment_groups_map.values())

    return render(request, 'portal/admin_work_zones.html', {
        'employees': employees,
        'zones': zones,
        'assignments': assignments,
        'assignment_groups': assignment_groups,
        'feedback': feedback,
        'feedback_level': feedback_level,
    })


# =========================================================
# APERTURA CEDOLINO + EMAIL NOTIFICA LETTURA
# =========================================================

@login_required
def open_payslip(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id)

    if not request.user.is_staff and payslip.employee.user != request.user:
        return HttpResponse("Non autorizzato", status=403)

    if not request.user.is_staff:
        view, created = PayslipView.objects.get_or_create(payslip=payslip)

        # Se è la prima visualizzazione invia email
        if created:
            send_read_notification_email(payslip)

        # Audit: apertura cedolino da parte del dipendente
        _create_audit_event(
            request,
            "payslip_opened",
            employee=payslip.employee,
            payslip=payslip,
            metadata={"first_view": created},
        )

    # Reindirizza sempre all'URL pubblico del PDF (R2 gestisce la visualizzazione/download)
    try:
        url = payslip.pdf.url
        return HttpResponseRedirect(url)
    except Exception:
        logger.exception('open_payslip: failed to build payslip URL id=%s', payslip_id)
        return HttpResponse('Errore nel recupero del file', status=500)


@login_required
def open_cud(request, cud_id):
    """Apertura del PDF CUD annuale."""
    cud = get_object_or_404(Cud, id=cud_id)

    if not request.user.is_staff and cud.employee.user != request.user:
        return HttpResponse("Non autorizzato", status=403)

    # Tracciamento apertura e audit (solo se non staff)
    if not request.user.is_staff:
        view, created = CudView.objects.get_or_create(cud=cud)

        _create_audit_event(
            request,
            "cud_opened",
            employee=cud.employee,
            metadata={
                "year": cud.year,
                "first_view": created,
            },
        )

    try:
        url = cud.pdf.url
        return HttpResponseRedirect(url)
    except Exception:
        logger.exception('open_cud: failed to build CUD URL id=%s', cud_id)
        return HttpResponse('Errore nel recupero del file CUD', status=500)

# =========================================================
# ADMIN DASHBOARD
# =========================================================

@login_required
def admin_dashboard(request):
    if not user_has_full_admin_access(request.user):
        if user_has_today_markings_access(request.user):
            return redirect('today_markings_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action in {'approve_mark_request', 'reject_mark_request'}:
            req_id = request.POST.get('request_id')
            request_obj = WorkMarkRequest.objects.filter(id=req_id).select_related('employee').first()
            if request_obj:
                request_obj.status = (
                    WorkMarkRequest.STATUS_APPROVED
                    if action == 'approve_mark_request'
                    else WorkMarkRequest.STATUS_REJECTED
                )
                request_obj.review_note = (request.POST.get('review_note') or '').strip() or None
                request_obj.reviewed_by = request.user
                request_obj.reviewed_at = timezone.now()
                request_obj.save(update_fields=['status', 'review_note', 'reviewed_by', 'reviewed_at', 'updated_at'])

                if request_obj.status == WorkMarkRequest.STATUS_APPROVED:
                    _apply_approved_mark_request_to_session(request_obj)

                _create_audit_event(
                    request,
                    'timekeeping_out_of_zone_reviewed',
                    employee=request_obj.employee,
                    metadata={
                        'request_id': request_obj.id,
                        'work_date': str(request_obj.work_date),
                        'status': request_obj.status,
                        'mark_type': request_obj.mark_type,
                        'marked_at': request_obj.created_at.isoformat() if request_obj.status == WorkMarkRequest.STATUS_APPROVED else None,
                        'via': 'admin_dashboard',
                    },
                )

            return redirect('admin_dashboard')

    today = timezone.localdate()
    _sync_approved_requests_for_range(today, today)
    pending_mark_requests = (
        WorkMarkRequest.objects
        .select_related('employee')
        .filter(status=WorkMarkRequest.STATUS_PENDING)
        .order_by('-created_at')[:15]
    )
    pending_mark_requests_count = WorkMarkRequest.objects.filter(status=WorkMarkRequest.STATUS_PENDING).count()

    month_start = today.replace(day=1)
    monthly_requests = WorkMarkRequest.objects.filter(created_at__date__gte=month_start, created_at__date__lte=today)

    today_marked_sessions = (
        WorkSession.objects
        .select_related('employee')
        .filter(work_date=today)
        .filter(
            Q(started_at__isnull=False)
            | Q(ended_at__isnull=False)
            | Q(corrected_started_at__isnull=False)
            | Q(corrected_ended_at__isnull=False)
        )
        .order_by('employee__last_name', 'employee__first_name')
    )

    entered_today_count = today_marked_sessions.filter(
        Q(started_at__isnull=False) | Q(corrected_started_at__isnull=False)
    ).count()
    completed_today_count = today_marked_sessions.filter(
        (Q(started_at__isnull=False) | Q(corrected_started_at__isnull=False))
        & (Q(ended_at__isnull=False) | Q(corrected_ended_at__isnull=False))
    ).count()
    incomplete_today_count = max(entered_today_count - completed_today_count, 0)
    outside_today_count = today_marked_sessions.filter(
        (Q(start_zone__isnull=False) & Q(start_within_zone=False))
        | (Q(end_zone__isnull=False) & Q(end_within_zone=False))
    ).count()
    approved_month_count = monthly_requests.filter(status=WorkMarkRequest.STATUS_APPROVED).count()
    rejected_month_count = monthly_requests.filter(status=WorkMarkRequest.STATUS_REJECTED).count()
    active_zone_count = WorkZone.objects.filter(is_active=True).count()
    active_assignment_count = EmployeeWorkZone.objects.filter(
        is_active=True,
        valid_from__lte=today,
    ).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=today)
    ).count()
    employee_count = Employee.objects.count()

    return render(request, "portal/admin_dashboard.html", {
        "entered_today_count": entered_today_count,
        "completed_today_count": completed_today_count,
        "incomplete_today_count": incomplete_today_count,
        "outside_today_count": outside_today_count,
        "approved_month_count": approved_month_count,
        "rejected_month_count": rejected_month_count,
        "pending_mark_requests_count": pending_mark_requests_count,
        "active_zone_count": active_zone_count,
        "active_assignment_count": active_assignment_count,
        "employee_count": employee_count,
        "today": today,
        "pending_mark_requests": pending_mark_requests,
        "today_marked_sessions": today_marked_sessions,
    })


def _today_marked_sessions_queryset(today):
    return (
        WorkSession.objects
        .select_related('employee')
        .filter(work_date=today)
        .filter(
            Q(started_at__isnull=False)
            | Q(ended_at__isnull=False)
            | Q(corrected_started_at__isnull=False)
            | Q(corrected_ended_at__isnull=False)
        )
        .order_by('employee__last_name', 'employee__first_name')
    )


@login_required
def today_markings_dashboard(request):
    if not user_has_today_markings_access(request.user) and not user_has_full_admin_access(request.user):
        return redirect('dashboard')

    today = timezone.localdate()
    _sync_approved_requests_for_range(today, today)
    today_marked_sessions = _today_marked_sessions_queryset(today)

    response = render(request, 'portal/today_markings_dashboard.html', {
        'today': today,
        'today_marked_sessions': today_marked_sessions,
    })
    return _disable_response_cache(response)


@login_required
def admin_upload_cud(request):
    """Upload manuale di un singolo CUD (annuale) per un dipendente."""
    if not request.user.is_staff:
        return redirect('dashboard')

    from django import forms

    class CudUploadForm(forms.Form):
        employee = forms.ModelChoiceField(queryset=Employee.objects.order_by('last_name', 'first_name'))
        year = forms.IntegerField(min_value=2000, max_value=2100)
        pdf = forms.FileField()

    success = False
    replaced = False
    cud_obj = None

    if request.method == 'POST':
        form = CudUploadForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.cleaned_data['employee']
            year = form.cleaned_data['year']
            pdf_file = form.cleaned_data['pdf']

            with transaction.atomic():
                existing = Cud.objects.filter(employee=employee, year=year).first()
                if existing:
                    try:
                        existing.pdf.delete(save=False)
                    except Exception:
                        logger.exception('Error deleting existing CUD file for %s', existing.id)
                    existing.delete()
                    replaced = True

                cud_obj = Cud(employee=employee, year=year)
                cud_obj.pdf.save(pdf_file.name, pdf_file, save=True)

            _create_audit_event(
                request,
                "cud_uploaded",
                employee=employee,
                metadata={"year": year, "replaced": replaced},
            )

            success = True
    else:
        from django.utils import timezone
        form = CudUploadForm(initial={"year": timezone.now().year})

    return render(request, "portal/admin_upload_cud.html", {
        "form": form,
        "success": success,
        "replaced": replaced,
        "cud": cud_obj,
    })


@login_required
def admin_report(request):
    """Report sintetico visualizzazioni cedolini per dipendente."""
    if not request.user.is_staff:
        return redirect('dashboard')

    employees_stats = (
        Employee.objects
        .annotate(
            totale=Count('payslips', distinct=True),
            visualizzati=Count('payslips', filter=Q(payslips__payslipview__isnull=False), distinct=True),
        )
        .order_by('last_name', 'first_name')
    )

    rows = []
    totale_cedolini = 0
    totale_visualizzati = 0

    for emp in employees_stats:
        totale = emp.totale
        visualizzati = emp.visualizzati
        non_visualizzati = max(totale - visualizzati, 0)

        totale_cedolini += totale
        totale_visualizzati += visualizzati

        rows.append({
            'employee': emp,
            'total': totale,
            'visualizzati': visualizzati,
            'non_visualizzati': non_visualizzati,
        })

    totale_non_visualizzati = max(totale_cedolini - totale_visualizzati, 0)

    return render(request, "portal/admin_report.html", {
        "rows": rows,
        "totale_cedolini": totale_cedolini,
        "totale_visualizzati": totale_visualizzati,
        "totale_non_visualizzati": totale_non_visualizzati,
    })


# =========================================================
# ADMIN: CONTROLLO INTEGRITÀ CEDOLINI
# =========================================================

@login_required
def admin_payslip_integrity(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    from django.core.files.storage import default_storage

    year = request.GET.get('year')
    employee_id = request.GET.get('employee')

    payslips_qs = Payslip.objects.all().select_related('employee').order_by('-year', '-month')

    if year:
        payslips_qs = payslips_qs.filter(year=year)
    if employee_id:
        payslips_qs = payslips_qs.filter(employee_id=employee_id)

    # Limite di sicurezza per non bombardare lo storage
    payslips_qs = payslips_qs[:2000]

    missing = []
    checked = 0

    for p in payslips_qs:
        checked += 1
        try:
            exists = default_storage.exists(p.pdf.name)
        except Exception:
            logger.exception("Errore nel controllo esistenza file per payslip id=%s", p.id)
            exists = False

        if not exists:
            missing.append(p)

    missing_count = len(missing)
    missing_ratio = (missing_count / checked) if checked else 0

    if missing_count == 0:
        integrity_status = "ok"
        integrity_label = "OK"
        integrity_reason = "Nessun PDF mancante rilevato."
    elif missing_ratio <= 0.05:
        integrity_status = "warning"
        integrity_label = "Attenzione"
        integrity_reason = "Anomalie limitate: presenza di pochi PDF mancanti."
    else:
        integrity_status = "critical"
        integrity_label = "Critica"
        integrity_reason = "Anomalie elevate: numero significativo di PDF mancanti."

    employees = Employee.objects.order_by('last_name', 'first_name')

    return render(request, "portal/admin_payslip_integrity.html", {
        "employees": employees,
        "year_selected": year,
        "employee_selected": int(employee_id) if employee_id else None,
        "checked": checked,
        "missing": missing,
        "missing_count": missing_count,
        "missing_percentage": round(missing_ratio * 100, 1),
        "integrity_status": integrity_status,
        "integrity_label": integrity_label,
        "integrity_reason": integrity_reason,
    })


@login_required
def admin_all_payslips(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    year = request.GET.get('year')
    month = request.GET.get('month')
    employee_id = request.GET.get('employee')

    payslips = Payslip.objects.select_related('employee__user').order_by('-year', '-month')

    if year:
        payslips = payslips.filter(year=year)
    if month:
        payslips = payslips.filter(month=month)
    if employee_id:
        payslips = payslips.filter(employee_id=employee_id)

    # CUD: usiamo gli stessi filtri per anno e dipendente (mese non rilevante)
    cuds = Cud.objects.select_related('employee__user').order_by('-year')
    if year:
        cuds = cuds.filter(year=year)
    if employee_id:
        cuds = cuds.filter(employee_id=employee_id)

    # arricchisci con info di visualizzazione
    cuds_list = []
    for c in cuds:
        view = CudView.objects.filter(cud=c).order_by('viewed_at').first()
        c.is_viewed = bool(view)
        c.viewed_at = view.viewed_at if view else None
        cuds_list.append(c)

    # Export CSV opzionale
    export_format = request.GET.get('format')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cedolini.csv"'

        writer = csv.writer(response)
        writer.writerow(['Dipendente', 'Codice esterno', 'Anno', 'Mese', 'Caricato il', 'ID'])
        for p in payslips:
            writer.writerow([
                getattr(p.employee, 'full_name', str(p.employee)),
                getattr(p.employee, 'external_code', ''),
                p.year,
                p.month,
                p.uploaded_at,
                p.id,
            ])
        return response

    employees = Employee.objects.order_by('last_name', 'first_name')

    return render(request, 'portal/admin_all_payslips.html', {
        'payslips': payslips,
        'cuds': cuds_list,
        'employees': employees,
        'year_selected': year,
        'month_selected': month,
        'employee_selected': int(employee_id) if employee_id else None,
    })


@login_required
def admin_audit_events(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    qs = AuditEvent.objects.select_related('actor_user', 'employee', 'payslip').order_by('-created_at')

    # simple filtering by action or employee id
    action = request.GET.get('action')
    emp = request.GET.get('employee')
    if action:
        qs = qs.filter(action__icontains=action)
    if emp:
        qs = qs.filter(employee__id=emp)

    paginator = Paginator(qs, 50)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    return render(request, 'portal/admin_audit_events.html', {
        'page_obj': page_obj,
        'action': action or '',
        'employee_filter': emp or '',
    })


@login_required
def admin_import_jobs(request):
    """Storico dei caricamenti cedolini (ImportJob)."""
    if not request.user.is_staff:
        return redirect('dashboard')

    jobs = ImportJob.objects.order_by('-created_at')

    paginator = Paginator(jobs, 50)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    return render(request, 'portal/admin_import_jobs.html', {
        'page_obj': page_obj,
    })


@login_required
def admin_import_job_payslips(request, job_id):
    """Mostra i cedolini caricati nello stesso intervallo temporale di un ImportJob.

    Non avendo un collegamento diretto ImportJob->Payslip, usiamo una finestra
    temporale intorno a created_at, sufficiente per i caricamenti batch normali.
    """
    if not request.user.is_staff:
        return redirect('dashboard')

    job = get_object_or_404(ImportJob, id=job_id)

    # finestra di 10 minuti intorno al job
    window = timedelta(minutes=10)
    start = job.created_at - window
    end = job.created_at + window

    payslips = (
        Payslip.objects
        .select_related('employee__user')
        .filter(uploaded_at__range=(start, end))
        .order_by('-uploaded_at')
    )

    return render(request, 'portal/admin_import_job_payslips.html', {
        'job': job,
        'payslips': payslips,
        'start': start,
        'end': end,
    })


@login_required
def admin_employees(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    employees = list(
        Employee.objects
        .select_related('user')
        .annotate(payslip_count=Count('payslips'))
        .order_by('last_name', 'first_name')
    )

    registered_employees = [employee for employee in employees if employee.privacy_accepted]
    invited_employees = [employee for employee in employees if not employee.privacy_accepted and employee.invito_inviato]
    not_invited_employees = [employee for employee in employees if not employee.privacy_accepted and not employee.invito_inviato]

    employee_sections = [
        {
            'id': 'registeredEmployees',
            'title': 'Utenti registrati',
            'subtitle': 'Dipendenti che hanno completato la registrazione e accettato la privacy.',
            'employees': registered_employees,
            'count': len(registered_employees),
            'expanded': False,
            'badge_class': 'bg-primary',
            'empty_message': 'Nessun dipendente registrato al momento.',
        },
        {
            'id': 'invitedEmployees',
            'title': 'Invitati',
            'subtitle': 'Dipendenti che hanno ricevuto l\'invito ma non hanno ancora completato la registrazione.',
            'employees': invited_employees,
            'count': len(invited_employees),
            'expanded': False,
            'badge_class': 'bg-success',
            'empty_message': 'Nessun dipendente nello stato invitato.',
        },
        {
            'id': 'notInvitedEmployees',
            'title': 'Non invitati',
            'subtitle': 'Dipendenti da contattare o da invitare per l\'accesso al portale.',
            'employees': not_invited_employees,
            'count': len(not_invited_employees),
            'expanded': False,
            'badge_class': 'bg-warning text-dark',
            'empty_message': 'Nessun dipendente da invitare.',
        },
    ]

    return render(request, 'portal/admin_employees.html', {
        'employees': employees,
        'employee_sections': employee_sections,
        'employee_total_count': len(employees),
    })


@login_required
def admin_employee_detail(request, emp_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    employee = get_object_or_404(Employee, id=emp_id)

    feedback = None
    feedback_level = 'success'

    if request.method == 'POST' and request.POST.get('action') == 'delete_payslip':
        payslip_id = request.POST.get('payslip_id')
        payslip = Payslip.objects.filter(id=payslip_id, employee=employee).first()

        if not payslip:
            return redirect(f'{request.path}?outcome=missing')

        payload = {
            'payslip_id': payslip.id,
            'year': payslip.year,
            'month': payslip.month,
            'pdf': payslip.pdf.name,
        }

        try:
            if payslip.pdf:
                payslip.pdf.delete(save=False)
        except Exception:
            logger.exception('Errore eliminazione file cedolino id=%s', payslip.id)

        payslip.delete()

        _create_audit_event(
            request,
            'payslip_deleted',
            employee=employee,
            metadata=payload,
        )

        return redirect(f'{request.path}?outcome=deleted')

    outcome = (request.GET.get('outcome') or '').strip()
    if outcome == 'deleted':
        feedback = 'Cedolino eliminato definitivamente.'
        feedback_level = 'warning'
    elif outcome == 'missing':
        feedback = 'Cedolino non trovato o gia eliminato.'
        feedback_level = 'danger'

    payslips = Payslip.objects.filter(employee=employee).order_by('-year', '-month')

    logger.info('admin_employee_detail: employee=%s payslip_count=%d', getattr(employee, 'id', None), payslips.count())
    try:
        ids = list(payslips.values_list('id', flat=True))
        logger.info('admin_employee_detail: payslip_ids=%s', ids)
    except Exception:
        logger.exception('admin_employee_detail: error listing payslip ids for employee=%s', getattr(employee, 'id', None))

    detailed = []
    for p in payslips:
        view = PayslipView.objects.filter(payslip=p).first()
        detailed.append({'payslip': p, 'view': view})

    # CUD del dipendente con info di visualizzazione
    cuds = Cud.objects.filter(employee=employee).order_by('-year')
    cuds_detailed = []
    for c in cuds:
        view = CudView.objects.filter(cud=c).first()
        cuds_detailed.append({'cud': c, 'view': view})

    return render(request, 'portal/admin_employee_detail.html', {
        'employee': employee,
        'detailed': detailed,
        'cuds_detailed': cuds_detailed,
        'feedback': feedback,
        'feedback_level': feedback_level,
    })


@login_required
def admin_reset_payslip_view(request, payslip_id):
    """Consente all'admin di azzerare lo stato di visualizzazione di un cedolino."""
    if not request.user.is_staff:
        return HttpResponse(status=403)

    payslip = get_object_or_404(Payslip, id=payslip_id)

    if request.method == 'POST':
        PayslipView.objects.filter(payslip=payslip).delete()

        _create_audit_event(
            request,
            "payslip_view_reset",
            employee=payslip.employee,
            payslip=payslip,
        )

    return redirect('admin_employee_detail', emp_id=payslip.employee_id)


@login_required
def admin_employee_payslips(request, emp_id):
    if not request.user.is_staff:
        return HttpResponse(status=403)

    employee = get_object_or_404(Employee, id=emp_id)
    payslips = Payslip.objects.filter(employee=employee).order_by('-year', '-month')

    return render(request, 'portal/_employee_payslips.html', {
        'payslips': payslips,
        'employee': employee,
    })


@login_required
def portal_tutorial(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')

    employee = Employee.objects.filter(user=request.user).first()
    if not employee:
        return HttpResponse("Profilo dipendente non trovato. Contatta l'amministratore.", status=403)

    return render(request, 'portal/tutorial.html', {
        'employee': employee,
    })


@login_required
def admin_send_invite(request):
    if not request.user.is_staff:
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

    if request.method != 'POST':
            action = request.POST.get('action')

    emp_id = request.POST.get('employee_id')
    email = request.POST.get('email')

    logger.info('admin_send_invite START user=%s emp_id=%s email_present=%s', getattr(request.user, 'username', None), emp_id, bool(email))

    if not emp_id:
        return JsonResponse({'ok': False, 'error': 'missing employee_id'}, status=400)

    try:
        employee = Employee.objects.select_related('user').get(id=emp_id)
    except Employee.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)

    logger.info('admin_send_invite: target employee=%s username=%s current_email=%s', getattr(employee, 'id', None), getattr(employee.user, 'username', None), employee.email_invio)

    # if email provided, set it
    if email:
        employee.email_invio = email
        employee.save()

        logger.info('admin_send_invite: updated email for employee=%s -> %s', employee.id, email)

    if not employee.email_invio:
        return JsonResponse({'ok': False, 'need_email': True})

    # create token and send email (reuse admin email template)
    from django.utils.crypto import get_random_string
    from django.utils import timezone
    from datetime import timedelta

    try:
        token = get_random_string(64)
        InviteToken.objects.create(employee=employee, token=token, expires_at=timezone.now() + timedelta(days=7))
    except Exception:
        logger.exception('admin_send_invite: error creating InviteToken for employee=%s', employee.id)
        return JsonResponse({'ok': False, 'error': 'token_error'})

    link = f"https://cedolini-web.onrender.com/portal/register/{token}/"
    username = employee.user.username

    subject = "Attivazione account - Portale Cedolini"
    text_content = (
        f"Gentile {employee.first_name or ''} {employee.last_name or ''},\n\n"
        f"è stato creato il tuo accesso al Portale Cedolini.\n\n"
        f"USERNAME: {username}\n\n"
        f"EMAIL: {employee.email_invio}\n\n"
        f"Clicca sul link seguente per attivare il tuo account e creare la password:\n{link}\n\n"
        f"Il link è valido per 7 giorni.\n\n"
        f"Dopo l'attivazione potrai accedere usando il tuo username oppure la tua email.\n\n"
        f"Per accedere al portale utilizza sempre questo indirizzo:\n"
        f"https://cedolini-web.onrender.com/login/\n"
    )

    html_content = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:Arial, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
<tr>
<td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;padding:40px;">
    <tr>
        <td align="center" style="padding-bottom:20px;">
            <img src="https://cedolini-web.onrender.com/static/portal/logo.png" width="120">
        </td>
    </tr>
    <tr>
        <td style="font-size:24px;font-weight:bold;color:#1f2937;padding-bottom:8px;">Attivazione Portale Cedolini</td>
    </tr>
    <tr>
        <td style="font-size:13px;color:#6b7280;padding-bottom:24px;">
            Accesso sicuro ai tuoi cedolini online
        </td>
    </tr>
    <tr>
        <td style="font-size:14px;color:#374151;padding-bottom:20px;line-height:1.6;">
            Gentile <strong>{employee.first_name or ''} {employee.last_name or ''}</strong>,<br><br>
            è stato creato il tuo accesso al <strong>Portale Cedolini</strong>.<br><br>
            Il tuo <strong style="color:#111827;">USERNAME</strong> per accedere è:<br>
            <span style="display:inline-block;margin-top:10px;padding:10px 14px;background:#eff6ff;border-radius:6px;font-family:monospace;font-size:15px;color:#111827;border:1px solid #bfdbfe;">
                {username}
            </span>
            <br><br>
            La tua <strong style="color:#111827;">EMAIL</strong> associata è:<br>
            <span style="display:inline-block;margin-top:10px;padding:10px 14px;background:#eff6ff;border-radius:6px;font-family:monospace;font-size:15px;color:#111827;border:1px solid #bfdbfe;">
                {employee.email_invio}
            </span>
        </td>
    </tr>
    <tr>
        <td align="center" style="padding:30px 0;">
            <a href="{link}" style="background:#2563eb;color:#ffffff;padding:14px 28px;text-decoration:none;border-radius:6px;font-weight:bold;">Attiva il tuo account</a>
        </td>
    </tr>
    <tr>
        <td style="font-size:12px;color:#6b7280;padding-top:10px;">
            Il link è valido per 7 giorni.
        </td>
    </tr>
    <tr>
        <td style="font-size:13px;color:#374151;padding-top:10px;line-height:1.6;">
            Dopo l'attivazione potrai accedere con <strong>USERNAME</strong> oppure con la tua <strong>EMAIL</strong>.
        </td>
    </tr>
    <tr>
        <td style="font-size:13px;color:#374151;padding-top:10px;">
            Per accedere al portale utilizza sempre questo indirizzo:<br>
            <a href="https://cedolini-web.onrender.com/login/" style="display:inline-block;margin-top:8px;padding:8px 12px;background:#0f172a;color:#ffffff;text-decoration:none;border-radius:4px;font-size:13px;">
                https://cedolini-web.onrender.com/login/
            </a>
        </td>
    </tr>
    <tr>
        <td style="font-size:12px;color:#9ca3af;padding-top:20px;">© San Vincenzo Srl</td>
    </tr>
</table>
</td>
</tr>
</table>
</body>
</html>
"""

    from django.core.mail import EmailMultiAlternatives
    try:
        email_msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [employee.email_invio], cc=["cedolini@sanvincenzosrl.com"])
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send()

        employee.invito_inviato = True
        employee.save()

        # Audit: invito inviato a un dipendente
        _create_audit_event(
            request,
            "invite_sent",
            employee=employee,
            metadata={
                "email": employee.email_invio,
            },
        )

        logger.info('admin_send_invite: email sent to %s for employee=%s', employee.email_invio, employee.id)
        return JsonResponse({'ok': True})
    except Exception:
        logger.exception('admin_send_invite: failed sending email to %s for employee=%s', employee.email_invio, employee.id)
        return JsonResponse({'ok': False, 'error': 'send_failed'})


@login_required
def admin_create_invite_link(request):
    """Crea (o riusa) un link di invito senza inviare email.

    Usato dall'area admin per copiare il link e inviarlo manualmente
    via WhatsApp / SMS.
    """
    if not request.user.is_staff:
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'method'}, status=405)

    emp_id = request.POST.get('employee_id')
    if not emp_id:
        return JsonResponse({'ok': False, 'error': 'missing employee_id'}, status=400)

    try:
        employee = Employee.objects.select_related('user').get(id=emp_id)
    except Employee.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)

    # Riusa un token valido se esiste, altrimenti creane uno nuovo
    invite = (
        InviteToken.objects
        .filter(employee=employee, used=False, expires_at__gt=timezone.now())
        .order_by('-created_at')
        .first()
    )

    if not invite:
        invite = InviteToken.objects.create(employee=employee)

    link = f"https://cedolini-web.onrender.com/portal/register/{invite.token}/"

    # Segna che un invito è stato generato
    employee.invito_inviato = True
    employee.save(update_fields=['invito_inviato'])

    # Testo precompilato in stile email di invito, da incollare in WhatsApp/SMS
    username = employee.user.username
    full_name = employee.full_name
    message = (
        f"Gentile {full_name},\n\n"
        f"è stato creato il tuo accesso al Portale Cedolini.\n\n"
        f"USERNAME: {username}\n\n"
        f"Per attivare il tuo account e creare la password utilizza questo link:\n"
        f"{link}\n\n"
        f"Il link è valido per 7 giorni.\n\n"
        f"Per i prossimi accessi al portale utilizza sempre questo indirizzo:\n"
        f"https://cedolini-web.onrender.com/login/\n\n"
        f"Cordiali saluti\n"
        f"San Vincenzo Srl"
    )

    # Audit: link invito creato per invio manuale
    _create_audit_event(
        request,
        "invite_link_created",
        employee=employee,
        metadata={
            "invite_token_id": invite.id,
            "via": "manual",
        },
    )

    return JsonResponse({
        'ok': True,
        'link': link,
        'username': employee.user.username,
        'full_name': employee.full_name,
        'message': message,
    })

def send_read_notification_email(payslip):

    employee = payslip.employee
    user = employee.user

    subject = "Cedolino visualizzato - Portale Cedolini"

    text_content = f"""
Il cedolino di {employee.first_name} {employee.last_name}
({payslip.month}/{payslip.year})
è stato visualizzato in data {timezone.now().strftime("%d/%m/%Y %H:%M")}.
"""

    html_content = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:Arial, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
<tr>
<td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;padding:40px;">
    
    <tr>
        <td align="center" style="padding-bottom:20px;">
            <img src="https://cedolini-web.onrender.com/static/portal/logo.png" width="120">
        </td>
    </tr>

    <tr>
        <td style="font-size:20px;font-weight:bold;color:#1f2937;padding-bottom:20px;">
            Cedolino Visualizzato
        </td>
    </tr>

    <tr>
        <td style="font-size:14px;color:#374151;padding-bottom:20px;">
            Il dipendente <strong>{employee.first_name} {employee.last_name}</strong><br>
            ha visualizzato il cedolino di <strong>{payslip.month}/{payslip.year}</strong>.
        </td>
    </tr>

    <tr>
        <td style="font-size:13px;color:#6b7280;">
            Data e ora: {timezone.now().strftime("%d/%m/%Y %H:%M")}
        </td>
    </tr>

</table>
</td>
</tr>
</table>
</body>
</html>
"""

    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        ["cedolini@sanvincenzosrl.com"],
    )

    email.attach_alternative(html_content, "text/html")
    email.send()


# =========================================================
# ADMIN: Upload folder / multiple payslips import
# =========================================================

@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    created_users = []
    created_payslips = []
    skipped = []

    months_map = {
        'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
        'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
        'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12,
    }

    # Two-phase flow:
    # - initial POST with files: process files and create users/payslips, store created ids in session and show confirmation
    # - confirmation page has Annulla which will call admin_cancel_import to rollback created items
    if request.method == 'POST' and request.FILES:
        # accept either input name 'files' or legacy 'folder' from template
        files = request.FILES.getlist('files') or request.FILES.getlist('folder')

        total_files = len(files)
        job = ImportJob.objects.create(
            total_files=total_files,
            status="processing",
        )

        processed_files = 0

        try:
            for f in files:
                processed_files += 1
                # filename without extension
                name = os.path.splitext(f.name)[0].strip()
                parts = name.split()
                if len(parts) < 3:
                    skipped.append((f.name, 'filename too short'))
                    continue

                # last token = year
                year_token = parts[-1]
                try:
                    year = int(year_token)
                except Exception:
                    skipped.append((f.name, 'invalid year'))
                    continue

                month_token = parts[-2].lower()
                month = months_map.get(month_token)
                if not month:
                    skipped.append((f.name, f'unknown month "{parts[-2]}"'))
                    continue

                name_tokens = parts[:-2]

                # Find existing employee trying different splits between last_name and first_name
                employee = None
                for i in range(1, len(name_tokens)):
                    last = ' '.join(name_tokens[:i]).strip()
                    first = ' '.join(name_tokens[i:]).strip()
                    qs = Employee.objects.filter(last_name__iexact=last, first_name__iexact=first)
                    if qs.exists():
                        employee = qs.first()
                        break

                # fallback: gestisci cognomi composti (Del Prete, Di Stefano, ...)
                # e, in generale, usa "prima parola = cognome" / resto = nome
                if not employee:
                    surname_particles = {
                        'DE', 'DEL', 'DELLA', 'DI', 'DA', 'DAL', 'DEI', 'DEGLI', 'DELL', "D'", 'D',
                    }

                    last = None
                    first = None

                    tokens_upper = [t.upper() for t in name_tokens]

                    # Esempio filename: "DEL PRETE RAFFAELE" -> cognome "DEL PRETE", nome "RAFFAELE"
                    if len(name_tokens) >= 3 and tokens_upper[0] in surname_particles:
                        last = ' '.join(name_tokens[:2]).strip()
                        first = ' '.join(name_tokens[2:]).strip()
                    else:
                        last = name_tokens[0]
                        first = ' '.join(name_tokens[1:]) if len(name_tokens) > 1 else ''

                    # prova ancora a cercare un dipendente esistente con questa combinazione
                    qs = Employee.objects.filter(last_name__iexact=last, first_name__iexact=first)
                    if qs.exists():
                        employee = qs.first()

                # If still not found, create user+employee
                if not employee:
                    # create unique username from full surname (all name_tokens before month/year)
                    base_username = '-'.join([t.lower() for t in name_tokens])
                    base_username = base_username.replace("'", '').replace('"', '')
                    username = base_username
                    suffix = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{suffix}"
                        suffix += 1

                    password = secrets.token_urlsafe(8)
                    user = User.objects.create_user(username=username, password=password, is_active=False)
                    employee = Employee.objects.create(user=user, first_name=first, last_name=last)
                    created_users.append(username)
                    # keep a record for template
                    if 'created_employees' not in locals():
                        created_employees = []
                    created_employees.append({'first_name': first, 'last_name': last, 'month': parts[-2], 'year': year, 'username': username})

                # create payslip if not exists — make atomic per file to avoid partial DB state
                try:
                    with transaction.atomic():
                        existing = Payslip.objects.filter(employee=employee, year=year, month=month).first()
                        if existing:
                            # delete existing file before replacing
                            try:
                                existing.pdf.delete(save=False)
                            except Exception:
                                logger.exception('Error deleting existing payslip file for %s', existing.id)
                            existing.delete()
                            logger.info('Removed duplicate payslip for employee=%s year=%s month=%s', employee.id, year, month)
                        ps = Payslip(employee=employee, year=year, month=month)
                        ps.pdf.save(f.name, f, save=True)
                        created_payslips.append(ps.id)
                except IntegrityError as ie:
                    logger.exception('IntegrityError creating payslip for file %s', f.name)
                    skipped.append((f.name, 'integrity error'))
                except Exception as e:
                    logger.exception('Error creating payslip for file %s', f.name)
                    skipped.append((f.name, str(e)))
        except Exception:
            logger.exception('Unhandled error while processing uploaded files')
            # Add a generic error entry so the template can show something instead of raising 500
            skipped.append(('__internal__', 'Unhandled error during import — see logs'))
            job.status = "error"
            job.error_message = 'Unhandled error during import — see logs'
        finally:
            job.processed_files = processed_files
            job.created_users = len(created_users)
            job.created_payslips = len(created_payslips)
            job.skipped = len(skipped)
            if job.status == "processing":
                job.status = "completed"
            job.save()

        logger.info(
            'ImportJob %s completed: total=%s processed=%s created_users=%s created_payslips=%s skipped=%s status=%s',
            getattr(job, 'id', None),
            total_files,
            processed_files,
            len(created_users),
            len(created_payslips),
            len(skipped),
            job.status,
        )

        # Audit: import massivo cedolini completato (o terminato con errore)
        _create_audit_event(
            request,
            "payslip_import_completed",
            metadata={
                "import_job_id": job.id,
                "total_files": total_files,
                "processed_files": processed_files,
                "created_users": len(created_users),
                "created_payslips": len(created_payslips),
                "skipped": len(skipped),
                "status": job.status,
            },
        )

        # persist created identifiers in session for potential rollback if admin cancels
        request.session['last_import_created_users'] = created_users
        request.session['last_import_created_payslips'] = created_payslips

        # render summary
        return render(request, 'portal/admin_confirm_import.html', {
            'new_employees': created_employees if 'created_employees' in locals() else [],
            'created_users': created_users,
            'created_payslips': created_payslips,
            'skipped': skipped,
            'import_job': job,
        })

    recent_jobs = ImportJob.objects.order_by('-created_at')[:20]

    return render(request, 'portal/admin_upload_period_folder.html', {
        'import_jobs': recent_jobs,
    })


@login_required
def admin_cancel_import(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    if request.method != 'POST':
        return redirect('admin_upload_period_folder')

    created_usernames = request.session.pop('last_import_created_users', []) or []
    created_payslip_ids = request.session.pop('last_import_created_payslips', []) or []

    # delete payslips first
    try:
        Payslip.objects.filter(id__in=created_payslip_ids).delete()
    except Exception:
        logger.exception('Error deleting created payslips during cancel-import')

    # delete users (which will cascade to Employee)
    try:
        User.objects.filter(username__in=created_usernames).delete()
    except Exception:
        logger.exception('Error deleting created users during cancel-import')

    # Audit: annullamento ultimo import cedolini
    _create_audit_event(
        request,
        "payslip_import_cancelled",
        metadata={
            "deleted_users": len(created_usernames),
            "deleted_payslips": len(created_payslip_ids),
        },
    )

    return redirect('admin_upload_period_folder')