import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings

from .models import Employee, Payslip


# =============================
# NAVIGAZIONE PRINCIPALE
# =============================

def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('dashboard')
    return redirect('login')


@login_required
def dashboard(request):
    employee = get_object_or_404(Employee, user=request.user)

    # 🔥 obbligo cambio password
    if employee.must_change_password:
        return redirect('password_change')

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


# =============================
# REGISTRAZIONE
# =============================

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
        else:
            messages.error(request, "Le password non coincidono.")

    return render(request, 'register.html', {'employee': employee})


# =============================
# AREA AMMINISTRATIVA
# =============================

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    totale_cedolini = Payslip.objects.count()

    context = {
        "totale_cedolini": totale_cedolini,
        "visualizzati": 0,
        "non_visualizzati": 0,
    }

    return render(request, "portal/admin_dashboard.html", context)


@login_required
def admin_upload_payslip(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, 'portal/admin_upload_payslip.html')


@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    if request.method == "POST":

        files = request.FILES.getlist("folder")

        if not files:
            messages.error(request, "Nessun file selezionato.")
            return redirect("admin_upload_period_folder")

        created_users = 0
        linked_payslips = 0

        month_map = {
            "gennaio": 1,
            "febbraio": 2,
            "marzo": 3,
            "aprile": 4,
            "maggio": 5,
            "giugno": 6,
            "luglio": 7,
            "agosto": 8,
            "settembre": 9,
            "ottobre": 10,
            "novembre": 11,
            "dicembre": 12,
        }

        for file in files:

            filename = os.path.splitext(file.name)[0].lower()
            parts = filename.split()

            if len(parts) < 4:
                continue

            cognome = parts[0].capitalize()
            nome = parts[1].capitalize()
            mese_str = parts[2].lower()

            try:
                anno = int(parts[3])
            except:
                continue

            if mese_str not in month_map:
                continue

            mese = month_map[mese_str]

            # 🔥 username intelligente
            base_username = f"{nome.lower()}-{cognome.lower()}"
            username = base_username
            counter = 1

            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.filter(
                first_name=nome,
                last_name=cognome
            ).first()

            if not user:
                user = User.objects.create(
                    username=username,
                    first_name=nome,
                    last_name=cognome
                )
                user.set_password("cambiala")
                user.save()

                Employee.objects.create(
                    user=user,
                    full_name=f"{nome} {cognome}",
                    must_change_password=True
                )

                created_users += 1

            employee = user.employee

            payslip, created = Payslip.objects.get_or_create(
                employee=employee,
                year=anno,
                month=mese,
                defaults={"pdf": file}
            )

            if created:
                linked_payslips += 1

        messages.success(
            request,
            f"{linked_payslips} cedolini caricati. "
            f"{created_users} nuovi dipendenti creati."
        )

        return redirect("admin_upload_period_folder")

    return render(request, "portal/admin_upload_period_folder.html")


@login_required
def admin_report(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, 'portal/admin_report.html')


@login_required
def admin_audit_dashboard(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, 'portal/admin_audit.html')


# =============================
# TEST EMAIL
# =============================

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

        return HttpResponse(f"Email inviata correttamente! Risultato: {result}")

    except Exception as e:
        return HttpResponse(f"Errore invio email: {str(e)}")