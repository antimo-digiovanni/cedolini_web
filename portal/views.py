import os
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, FileResponse, HttpResponseRedirect
from django.db import transaction, IntegrityError
from django.db.models import Count
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import Employee, Payslip, PayslipView, ImportJob, InviteToken
from .models import AuditEvent
from django.core.paginator import Paginator

import logging
import secrets

logger = logging.getLogger(__name__)


# =========================================================
# HOME
# =========================================================

def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('dashboard')
    return redirect('login')


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
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if not first_name or not last_name or not password:
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

        user.first_name = first_name
        user.last_name = last_name
        user.set_password(password)
        user.is_active = True
        user.save()

        employee.first_name = first_name
        employee.last_name = last_name
        employee.must_change_password = False
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

        viewed = p.payslipview_set.exists()

        p.is_viewed = viewed
        p.viewed_at = None

        if p.year not in grouped:
            grouped[p.year] = []

        grouped[p.year].append(p)

    logger.info("about to render template")
    return render(request, 'portal/dashboard.html', {
        'employee': employee,
        'grouped_payslips': grouped
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

    # Serve il file usando lo storage configured (supporta S3/R2 or filesystem)
    from django.core.files.storage import default_storage
    try:
        # try to open with storage (works with S3-backed storages too)
        f = default_storage.open(payslip.pdf.name, 'rb')
        response = FileResponse(f, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(payslip.pdf.name)}"'
        return response
    except FileNotFoundError:
        logger.exception('open_payslip: file not found in storage for payslip id=%s name=%s', payslip_id, payslip.pdf.name)
        return HttpResponse('File non trovato', status=404)
    except Exception:
        # Some storages (or configuration) may not allow open; try redirecting to the file URL
        try:
            url = payslip.pdf.url
            return HttpResponseRedirect(url)
        except Exception:
            logger.exception('open_payslip: failed to serve or redirect payslip id=%s', payslip_id)
            return HttpResponse('Errore nel recupero del file', status=500)

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
def admin_all_payslips(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    payslips = Payslip.objects.select_related('employee__user').order_by('-year', '-month')
    return render(request, 'portal/admin_all_payslips.html', {
        'payslips': payslips
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

    return render(request, 'portal/admin_employee_detail.html', {
        'employee': employee,
        'detailed': detailed,
    })


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
        f"Clicca sul link seguente per attivare il tuo account e creare la password:\n{link}\n\n"
        f"Il link è valido per 7 giorni.\n\n"
        f"Per accedere in futuro al portale utilizza sempre questo indirizzo:\n"
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
        <td style="font-size:22px;font-weight:bold;color:#1f2937;padding-bottom:20px;">Attivazione Portale Cedolini</td>
    </tr>
    <tr>
        <td style="font-size:14px;color:#374151;padding-bottom:20px;">
            Gentile <strong>{employee.first_name or ''} {employee.last_name or ''}</strong>,<br><br>
            è stato creato il tuo accesso al Portale Cedolini.<br><br>
            Il tuo <strong>username</strong> per accedere è:<br>
            <span style="display:inline-block;margin-top:8px;padding:6px 10px;background:#f3f4f6;border-radius:4px;font-family:monospace;">
                {username}
            </span>
        </td>
    </tr>
    <tr>
        <td align="center" style="padding:30px 0;">
            <a href="{link}" style="background:#2563eb;color:#ffffff;padding:14px 28px;text-decoration:none;border-radius:6px;font-weight:bold;">Attiva il tuo account</a>
        </td>
    </tr>
    <tr>
        <td style="font-size:12px;color:#6b7280;">
            Il link è valido per 7 giorni.<br>
            Per accedere in futuro al portale utilizza sempre questo indirizzo:<br>
            <a href="https://cedolini-web.onrender.com/login/" style="color:#2563eb;text-decoration:none;">
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

        logger.info('admin_send_invite: email sent to %s for employee=%s', employee.email_invio, employee.id)
        return JsonResponse({'ok': True})
    except Exception:
        logger.exception('admin_send_invite: failed sending email to %s for employee=%s', employee.email_invio, employee.id)
        return JsonResponse({'ok': False, 'error': 'send_failed'})

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

                # fallback: surname = first token, firstname = rest
                if not employee:
                    last = name_tokens[0]
                    first = ' '.join(name_tokens[1:]) if len(name_tokens) > 1 else ''
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

    return redirect('admin_upload_period_folder')