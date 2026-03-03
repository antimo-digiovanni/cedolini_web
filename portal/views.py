import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

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
    employee = get_object_or_404(Employee, user=request.user)

    payslips = (
        Payslip.objects
        .filter(employee=employee)
        .prefetch_related("payslipview_set")
        .order_by('-year', '-month')
    )

    grouped = {}

    for p in payslips:
        viewed = p.payslipview_set.first()

        p.is_viewed = bool(viewed)
        p.viewed_at = viewed.created_at if viewed else None

        if p.year not in grouped:
            grouped[p.year] = []

        grouped[p.year].append(p)

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