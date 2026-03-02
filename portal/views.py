from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings

from .models import Employee, Payslip


# -----------------------------
# NAVIGAZIONE PRINCIPALE
# -----------------------------

def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('dashboard')
    return redirect('login')


@login_required
def dashboard(request):
    employee = get_object_or_404(Employee, user=request.user)
    payslips = Payslip.objects.filter(employee=employee).order_by('-year', '-month')

    return render(request, 'dashboard.html', {
        'employee': employee,
        'payslips': payslips
    })


@login_required
def open_payslip(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id)

    if not request.user.is_staff and payslip.employee.user != request.user:
        return HttpResponse("Non autorizzato", status=403)

    response = HttpResponse(payslip.pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="cedolino.pdf"'
    return response


# -----------------------------
# REGISTRAZIONE
# -----------------------------

def register_view(request, token):
    user_obj = get_object_or_404(User, username=token)
    employee = get_object_or_404(Employee, user=user_obj)

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password and password == confirm_password:
            user_obj.set_password(password)
            user_obj.save()

            employee.must_change_password = False
            employee.save()

            messages.success(request, "Registrazione completata!")
            return redirect('login')

    return render(request, 'register.html', {'employee': employee})


def activate_account(request, uidb64, token):
    return redirect('login')


# -----------------------------
# AREA AMMINISTRATIVA
# -----------------------------

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    return render(request, 'admin_dashboard.html')


@login_required
def admin_upload_payslip(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    return render(request, 'admin_upload.html')


@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    return HttpResponse("Upload cartella periodo - in costruzione")


@login_required
def admin_report(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    return render(request, 'admin_report.html')


@login_required
def admin_audit_dashboard(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    return render(request, 'admin_audit.html')


# -----------------------------
# TEST EMAIL (SOLO ADMIN)
# -----------------------------

@login_required
def test_email(request):
    if not request.user.is_staff:
        return HttpResponse("Non autorizzato", status=403)

    try:
        result = send_mail(
            subject='Test Gmail - Portale Cedolini',
            message='Configurazione Gmail OK!',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=['antimo.digiovanni@sanvincenzosrl.com'],
            fail_silently=False
        )

        return HttpResponse(f"✅ Email inviata correttamente! Risultato: {result}")

    except Exception as e:
        return HttpResponse(f"❌ Errore invio email: {str(e)}")


# -----------------------------
# FUNZIONI TAPPO
# -----------------------------

@login_required
def force_password_change_if_needed(request):
    return redirect('dashboard')


@login_required
def complete_profile(request):
    return redirect('dashboard')