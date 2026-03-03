import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from .models import Employee, Payslip, PayslipView, ImportJob, InviteToken


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
        password = request.POST.get("password")

        if not password or len(password) < 8:
            messages.error(request, "Password troppo corta (min 8 caratteri)")
            return redirect(request.path)

        user.set_password(password)
        user.is_active = True
        user.save()

        employee.must_change_password = False
        employee.save()

        invite.mark_used()

        messages.success(request, "Registrazione completata. Ora puoi accedere.")
        return redirect("login")

    return render(request, "portal/register.html", {
        "employee": employee
    })


# =========================================================
# INVIA INVITO EMAIL
# =========================================================

def send_invite_email(employee):

    invite = InviteToken.objects.create(employee=employee)

    register_url = f"https://cedolini-web.onrender.com/portal/register/{invite.token}/"

    subject = "Accesso Portale Cedolini"

    text_content = f"""
Gentile {employee.full_name},

è stato creato il tuo accesso al Portale Cedolini.

Username: {employee.user.username}

Clicca qui per completare la registrazione:
{register_url}

Il link scade tra 7 giorni.

Cordiali saluti
San Vincenzo Srl
"""

    html_content = f"""
<p>Gentile <strong>{employee.full_name}</strong>,</p>

<p>È stato creato il tuo accesso al <strong>Portale Cedolini</strong>.</p>

<p><strong>Username:</strong> {employee.user.username}</p>

<p>
<a href="{register_url}" 
style="display:inline-block;padding:12px 20px;background:#1f2937;color:white;text-decoration:none;border-radius:6px;">
Completa registrazione
</a>
</p>

<p>Il link scade tra 7 giorni.</p>

<p>Cordiali saluti<br>
San Vincenzo Srl</p>
"""

    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [employee.email_invio],
        cc=["cedolini@sanvincenzosrl.com"],
    )

    email.attach_alternative(html_content, "text/html")
    email.send()

    employee.invito_inviato = True
    employee.save()


# =========================================================
# AREA DIPENDENTE
# =========================================================

@login_required
def dashboard(request):
    employee = get_object_or_404(Employee, user=request.user)

    payslips = Payslip.objects.filter(
        employee=employee
    ).order_by('-year', '-month')

    return render(request, 'portal/dashboard.html', {
        'employee': employee,
        'payslips': payslips
    })


@login_required
def open_payslip(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id)

    if not request.user.is_staff and payslip.employee.user != request.user:
        return HttpResponse("Non autorizzato", status=403)

    if not request.user.is_staff:
        if not PayslipView.objects.filter(payslip=payslip).exists():
            PayslipView.objects.create(payslip=payslip)

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


# =========================================================
# IMPORT CARTELLA PERIODO
# =========================================================

@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    if request.method == "POST":

        files = request.FILES.getlist("folder")

        if not files:
            return JsonResponse({"error": "Nessun file"}, status=400)

        job = ImportJob.objects.create(
            total_files=len(files)
        )

        month_map = {
            "gennaio": 1, "febbraio": 2, "marzo": 3,
            "aprile": 4, "maggio": 5, "giugno": 6,
            "luglio": 7, "agosto": 8, "settembre": 9,
            "ottobre": 10, "novembre": 11, "dicembre": 12,
        }

        try:
            with transaction.atomic():

                employees = {
                    e.full_name.lower(): e
                    for e in Employee.objects.select_related("user")
                }

                usernames = set(
                    User.objects.values_list("username", flat=True)
                )

                existing_payslips = set(
                    Payslip.objects.values_list("employee_id", "year", "month")
                )

                for file in files:

                    filename = os.path.splitext(file.name)[0].strip().lower()
                    parts = filename.split()

                    if len(parts) < 4:
                        job.skipped += 1
                        continue

                    mese_str = parts[-2]
                    anno_str = parts[-1]

                    if mese_str not in month_map:
                        job.skipped += 1
                        continue

                    try:
                        anno = int(anno_str)
                    except:
                        job.skipped += 1
                        continue

                    name_parts = parts[:-2]
                    nome = name_parts[-1].capitalize()
                    cognome = " ".join(name_parts[:-1]).title()
                    full_name = f"{nome} {cognome}"
                    mese = month_map[mese_str]

                    employee = employees.get(full_name.lower())

                    if not employee:
                        base_username = nome.lower() + "-" + cognome.lower().replace(" ", "-")
                        username = base_username
                        counter = 1

                        while username in usernames:
                            username = f"{base_username}{counter}"
                            counter += 1

                        user = User.objects.create_user(
                            username=username,
                            password="cambiala",
                            first_name=nome,
                            last_name=cognome
                        )

                        employee = Employee.objects.create(
                            user=user,
                            full_name=full_name,
                            must_change_password=True
                        )

                        employees[full_name.lower()] = employee
                        usernames.add(username)
                        job.created_users += 1

                    if (employee.id, anno, mese) not in existing_payslips:
                        Payslip.objects.create(
                            employee=employee,
                            year=anno,
                            month=mese,
                            pdf=file
                        )
                        job.created_payslips += 1
                    else:
                        job.skipped += 1

                    job.processed_files += 1
                    job.save(update_fields=[
                        "processed_files",
                        "created_users",
                        "created_payslips",
                        "skipped"
                    ])

                job.status = "completed"
                job.save()

        except Exception as e:
            job.status = "error"
            job.error_message = str(e)
            job.save()
            return JsonResponse({"error": str(e)}, status=500)

        return JsonResponse({"job_id": job.id})

    return render(request, "portal/admin_upload_period_folder.html")


@login_required
def import_progress(request, job_id):
    job = get_object_or_404(ImportJob, id=job_id)

    percent = int((job.processed_files / job.total_files) * 100) if job.total_files else 0

    return JsonResponse({
        "percent": percent,
        "status": job.status,
        "created_users": job.created_users,
        "created_payslips": job.created_payslips,
        "skipped": job.skipped
    })