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
# REGISTER VIEW
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
# IMPORT CARTELLA PERIODO
# =========================================================

@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, "portal/admin_upload_period_folder.html")


# =========================================================
# UPLOAD SINGOLO CEDOLINO
# =========================================================

@login_required
def admin_upload_payslip(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, 'portal/admin_upload_payslip.html')


# =========================================================
# ADMIN AUDIT
# =========================================================

@login_required
def admin_audit_dashboard(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, 'portal/admin_audit.html')