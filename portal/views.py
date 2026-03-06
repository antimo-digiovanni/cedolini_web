import os
import csv
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, FileResponse, HttpResponseRedirect
from django.db import transaction, IntegrityError
from django.db.models import Count, Q
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import Employee, Payslip, PayslipView, ImportJob, InviteToken, Cud, CudView
from .models import AuditEvent
from django.core.paginator import Paginator

import logging
import secrets

logger = logging.getLogger(__name__)


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


# =========================================================
# HOME
# =========================================================

def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('dashboard')
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


def google_site_verification(request):
    """Serve il file di verifica Search Console al percorso richiesto da Google."""
    return HttpResponse(
        'google-site-verification: googlee8ce7f16b7b5fed5.html',
        content_type='text/plain',
    )


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
    logger.info("before get_object_or_404(Employee)")
    employee = get_object_or_404(Employee, user=request.user)
    logger.info("after get_object_or_404 employee_id=%s", getattr(employee, "id", None))

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
    return render(request, 'portal/dashboard.html', {
        'employee': employee,
        'grouped_payslips': grouped,
        'cuds': cuds,
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
    if not request.user.is_staff:
        return redirect('dashboard')

    totale_cedolini = Payslip.objects.count()
    totale_dipendenti = Employee.objects.count()

    visualizzati = Payslip.objects.filter(
        payslipview__isnull=False
    ).distinct().count()

    non_visualizzati = totale_cedolini - visualizzati

    return render(request, "portal/admin_dashboard.html", {
        "totale_cedolini": totale_cedolini,
        "totale_dipendenti": totale_dipendenti,
        "visualizzati": visualizzati,
        "non_visualizzati": non_visualizzati,
    })


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
    employees = Employee.objects.select_related('user').annotate(payslip_count=Count('payslips')).all().order_by('last_name', 'first_name')
    return render(request, 'portal/admin_employees.html', {
        'employees': employees
    })


@login_required
def admin_employee_detail(request, emp_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    employee = get_object_or_404(Employee, id=emp_id)
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
def admin_send_invite(request):
    if not request.user.is_staff:
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'method'}, status=405)

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