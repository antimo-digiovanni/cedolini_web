import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse

from .models import Employee, Payslip, PayslipView


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
# REGISTER
# =========================================================

def register_view(request, token):
    user = get_object_or_404(User, username=token)
    employee = get_object_or_404(Employee, user=user)

    if request.method == "POST":
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password and password == confirm:
            user.set_password(password)
            user.save()

            employee.must_change_password = False
            employee.save()

            messages.success(request, "Registrazione completata.")
            return redirect("login")
        else:
            messages.error(request, "Le password non coincidono.")

    return render(request, "portal/register.html", {
        "employee": employee
    })


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
# ADMIN EMPLOYEES
# =========================================================

@login_required
def admin_employees(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    employees = Employee.objects.select_related('user').all()

    return render(request, "portal/admin_employees.html", {
        "employees": employees
    })


# =========================================================
# ADMIN EMPLOYEE DETAIL
# =========================================================

@login_required
def admin_employee_detail(request, employee_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    employee = get_object_or_404(Employee, id=employee_id)
    payslips = employee.payslips.all().order_by('-year', '-month')

    return render(request, "portal/admin_employee_detail.html", {
        "employee": employee,
        "payslips": payslips
    })


# =========================================================
# ADMIN REPORT
# =========================================================

@login_required
def admin_report(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    employees = Employee.objects.all()
    report_data = []

    for emp in employees:
        totale = emp.payslips.count()

        visualizzati = Payslip.objects.filter(
            employee=emp,
            payslipview__isnull=False
        ).distinct().count()

        non_visualizzati = totale - visualizzati

        report_data.append({
            "employee": emp,
            "totale": totale,
            "visualizzati": visualizzati,
            "non_visualizzati": non_visualizzati,
        })

    return render(request, "portal/admin_report.html", {
        "report_data": report_data
    })


# =========================================================
# IMPORT CARTELLA PERIODO (FUNZIONANTE)
# =========================================================

@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    if request.method == "POST":

        files = request.FILES.getlist("folder")

        if not files:
            messages.error(request, "Nessun file selezionato.")
            return redirect("admin_upload_period_folder")

        month_map = {
            "gennaio": 1, "febbraio": 2, "marzo": 3,
            "aprile": 4, "maggio": 5, "giugno": 6,
            "luglio": 7, "agosto": 8, "settembre": 9,
            "ottobre": 10, "novembre": 11, "dicembre": 12,
        }

        created_users = 0
        created_payslips = 0
        skipped = 0

        for file in files:

            filename = os.path.splitext(file.name)[0].strip().lower()
            parts = filename.split()

            if len(parts) < 4:
                skipped += 1
                continue

            cognome = parts[0].capitalize()
            nome = parts[1].capitalize()
            mese_str = parts[2]

            try:
                anno = int(parts[3])
            except:
                skipped += 1
                continue

            if mese_str not in month_map:
                skipped += 1
                continue

            mese = month_map[mese_str]
            full_name = f"{nome} {cognome}"

            employee = Employee.objects.filter(
                full_name__iexact=full_name
            ).first()

            if not employee:

                base_username = f"{nome.lower()}-{cognome.lower()}"
                username = base_username
                counter = 1

                while User.objects.filter(username=username).exists():
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

                created_users += 1

            if not Payslip.objects.filter(
                employee=employee,
                year=anno,
                month=mese
            ).exists():

                Payslip.objects.create(
                    employee=employee,
                    year=anno,
                    month=mese,
                    pdf=file
                )

                created_payslips += 1
            else:
                skipped += 1

        messages.success(
            request,
            f"Import completato ✅ Cedolini: {created_payslips} | "
            f"Nuovi utenti: {created_users} | Saltati: {skipped}"
        )

        return redirect("admin_upload_period_folder")

    return render(request, "portal/admin_upload_period_folder.html")


# =========================================================
# UPLOAD SINGOLO
# =========================================================

@login_required
def admin_upload_payslip(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, "portal/admin_upload_payslip.html")


# =========================================================
# ADMIN AUDIT
# =========================================================

@login_required
def admin_audit_dashboard(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, "portal/admin_audit.html")