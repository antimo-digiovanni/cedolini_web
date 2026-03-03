import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db import transaction, IntegrityError
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import Employee, Payslip, PayslipView, ImportJob, InviteToken

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

    response = HttpResponse(payslip.pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="cedolino.pdf"'
    return response

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

    if request.method == 'POST' and request.FILES:
        # accept either input name 'files' or legacy 'folder' from template
        files = request.FILES.getlist('files') or request.FILES.getlist('folder')
        try:
            for f in files:
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
                    created_users.append((username, f.name))
                    # keep a record for template
                    if 'created_employees' not in locals():
                        created_employees = []
                    created_employees.append({'first_name': first, 'last_name': last, 'month': parts[-2], 'year': year})

                # create payslip if not exists — make atomic per file to avoid partial DB state
                try:
                    with transaction.atomic():
                        if Payslip.objects.filter(employee=employee, year=year, month=month).exists():
                            skipped.append((f.name, 'payslip already exists'))
                        else:
                            ps = Payslip(employee=employee, year=year, month=month)
                            ps.pdf.save(f.name, f, save=True)
                            created_payslips.append((employee.user.username, year, month))
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

        # render summary
        return render(request, 'portal/admin_confirm_import.html', {
            'new_employees': created_employees if 'created_employees' in locals() else [],
            'created_users': created_users,
            'created_payslips': created_payslips,
            'skipped': skipped,
        })

    return render(request, 'portal/admin_upload_period_folder.html')