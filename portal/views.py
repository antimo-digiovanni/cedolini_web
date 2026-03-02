import os
import calendar
import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.db.models import Count

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

    if employee.must_change_password:
        return redirect('password_change')

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

    # Registra visualizzazione (una sola volta per cedolino)
    if not request.user.is_staff:
        if not PayslipView.objects.filter(payslip=payslip).exists():
            PayslipView.objects.create(payslip=payslip)

    response = HttpResponse(payslip.pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="cedolino.pdf"'
    return response


# =========================================================
# REGISTRAZIONE
# =========================================================

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

    return render(request, 'portal/register.html', {
        'employee': employee
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

    # Distribuzione mensile anno corrente
    current_year = datetime.date.today().year

    monthly_data = (
        Payslip.objects
        .filter(year=current_year)
        .values('month')
        .annotate(total=Count('id'))
        .order_by('month')
    )

    month_labels = []
    month_counts = []

    for m in monthly_data:
        month_labels.append(calendar.month_name[m['month']])
        month_counts.append(m['total'])

    return render(request, "portal/admin_dashboard.html", {
        "totale_cedolini": totale_cedolini,
        "totale_dipendenti": totale_dipendenti,
        "visualizzati": visualizzati,
        "non_visualizzati": non_visualizzati,
        "month_labels": month_labels,
        "month_counts": month_counts,
    })


# =========================================================
# LISTA DIPENDENTI
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
# DETTAGLIO DIPENDENTE
# =========================================================

@login_required
def admin_employee_detail(request, employee_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    employee = get_object_or_404(Employee, id=employee_id)
    payslips = employee.payslips.all().order_by('-year', '-month')

    grouped = {}

    for p in payslips:
        year = p.year
        month_name = calendar.month_name[p.month]

        view = p.payslipview_set.order_by('-viewed_at').first()

        if year not in grouped:
            grouped[year] = []

        grouped[year].append({
            "payslip": p,
            "month_name": month_name,
            "view": view
        })

    return render(request, "portal/admin_employee_detail.html", {
        "employee": employee,
        "grouped": grouped
    })


# =========================================================
# REPORT GENERALE
# =========================================================

@login_required
def admin_report(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    employees = Employee.objects.all()

    report_data = []

    for emp in employees:
        total = emp.payslips.count()

        visualizzati = Payslip.objects.filter(
            employee=emp,
            payslipview__isnull=False
        ).distinct().count()

        non_visualizzati = total - visualizzati

        report_data.append({
            "employee": emp,
            "total": total,
            "visualizzati": visualizzati,
            "non_visualizzati": non_visualizzati,
        })

    return render(request, 'portal/admin_report.html', {
        "report_data": report_data
    })


# =========================================================
# RESET PASSWORD
# =========================================================

@login_required
def admin_reset_password(request, user_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    user = get_object_or_404(User, id=user_id)

    user.set_password("cambiala")
    user.save()

    employee = user.employee
    employee.must_change_password = True
    employee.save()

    messages.success(request, f"Password resettata per {employee.full_name}")
    return redirect("admin_employees")


# =========================================================
# GENERA LINK REGISTRAZIONE
# =========================================================

@login_required
def admin_generate_link(request, user_id):
    if not request.user.is_staff:
        return redirect('dashboard')

    user = get_object_or_404(User, id=user_id)

    link = request.build_absolute_uri(
        reverse("register_view", args=[user.username])
    )

    messages.success(request, f"Link registrazione: {link}")
    return redirect("admin_employees")


# =========================================================
# ALTRE PAGINE ADMIN
# =========================================================

@login_required
def admin_upload_payslip(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, 'portal/admin_upload_payslip.html')


@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, "portal/admin_upload_period_folder.html")


@login_required
def admin_audit_dashboard(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    return render(request, 'portal/admin_audit.html')