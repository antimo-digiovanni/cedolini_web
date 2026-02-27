import re
import uuid
import os
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404

from .models import Employee, Payslip

MONTHS_IT = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
    5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
    9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre",
}

MONTHS_IT_REV = {v.lower(): k for k, v in MONTHS_IT.items()}

# ==========================================================
# ✅ NAVIGAZIONE E PROFILO
# ==========================================================
@login_required
def home(request):
    return render(request, "portal/home.html")

@login_required
def complete_profile(request):
    return redirect("home")

@login_required
def force_password_change_if_needed(request):
    return redirect("home")

def activate_account(request, uidb64, token):
    """Placeholder per attivazione account via email."""
    messages.info(request, "Link di attivazione ricevuto.")
    return redirect("login")

# ==========================================================
# ✅ DASHBOARD ADMIN
# ==========================================================
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect("home")
    total_payslips = Payslip.objects.count()
    return render(request, "portal/admin_dashboard.html", {"total_payslips": total_payslips})

# ==========================================================
# ✅ IMPORT CARTELLA MESE
# ==========================================================
@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff:
        return redirect("home")

    report = {"saved_existing": 0, "new_found": 0, "errors": 0}

    if request.method == "POST":
        files = request.FILES.getlist("files")
        if not files:
            messages.error(request, "Seleziona uno o più PDF.")
            return redirect("admin_upload_period_folder")

        batch_id = str(uuid.uuid4())
        pending_dir = os.path.join(settings.MEDIA_ROOT, "pending", batch_id)
        os.makedirs(pending_dir, exist_ok=True)

        for f in files:
            try:
                filename = f.name
                name = filename.rsplit(".", 1)[0].strip()
                parts = name.split()
                if len(parts) < 4: raise ValueError("Formato non valido")

                last_name, first_name = parts[0].strip(), parts[1].strip()
                month_name, year = parts[2].strip().lower(), int(parts[3])

                if month_name not in MONTHS_IT_REV: raise ValueError("Mese non valido")

                month = MONTHS_IT_REV[month_name]
                full_name = f"{first_name} {last_name}".strip()
                employee = Employee.objects.filter(full_name__iexact=full_name).first()

                if not employee:
                    report["new_found"] += 1
                    continue

                pending_path = os.path.join(pending_dir, filename)
                with open(pending_path, "wb+") as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)

                Payslip.objects.update_or_create(
                    employee=employee, year=year, month=month,
                    defaults={'pdf': pending_path}
                )
                report["saved_existing"] += 1
            except Exception:
                report["errors"] += 1

        messages.success(request, f"Salvati: {report['saved_existing']}, Nuovi: {report['new_found']}, Errori: {report['errors']}")

    return render(request, "portal/admin_upload_period_folder.html", {"report": report})

# ==========================================================
# ✅ GESTIONE DIPENDENTI
# ==========================================================
@login_required
def admin_manage_employees(request):
    if not request.user.is_staff:
        return redirect("home")
    q = (request.GET.get("q") or "").strip()
    employees = Employee.objects.all().order_by("full_name")
    if q: employees = employees.filter(full_name__icontains=q)
    return render(request, "portal/admin_manage_employees.html", {"employees": employees, "q": q})

@login_required
def admin_employee_payslips(request, employee_id):
    if not request.user.is_staff:
        return redirect("home")
    employee = get_object_or_404(Employee, id=employee_id)
    payslips = Payslip.objects.filter(employee=employee).order_by("-year", "-month")
    return render(request, "portal/admin_employee_payslips.html", {"employee": employee, "payslips": payslips})

# ==========================================================
# ✅ VISUALIZZAZIONE PDF
# ==========================================================
@login_required
def open_payslip(request, payslip_id):
    if request.user.is_staff:
        payslip = get_object_or_404(Payslip, id=payslip_id)
    else:
        payslip = get_object_or_404(Payslip, id=payslip_id, employee__user=request.user)
    
    if not payslip.pdf: raise Http404("PDF mancante.")
    try:
        return FileResponse(payslip.pdf.open('rb'), content_type='application/pdf')
    except FileNotFoundError:
        raise Http404("File non trovato sul server.")