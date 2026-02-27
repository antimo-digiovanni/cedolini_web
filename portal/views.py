import re
import uuid
import os
from typing import Optional

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
# ✅ DASHBOARD ADMIN
# ==========================================================
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect("home")

    total_payslips = Payslip.objects.count()
    return render(request, "portal/admin_dashboard.html", {
        "total_payslips": total_payslips,
    })


# ==========================================================
# ✅ IMPORT CARTELLA MESE (VERSIONE STABILE)
# ==========================================================
@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff:
        return redirect("home")

    report = {
        "saved_existing": 0,
        "new_found": 0,
        "errors": 0,
    }

    if request.method == "POST":
        files = request.FILES.getlist("files")

        if not files:
            messages.error(request, "Seleziona uno o più PDF.")
            return render(request, "portal/admin_upload_period_folder.html", {"report": report})

        batch_id = str(uuid.uuid4())
        pending_dir = os.path.join(settings.MEDIA_ROOT, "pending", batch_id)
        os.makedirs(pending_dir, exist_ok=True)

        for f in files:
            try:
                filename = f.name
                name = filename.rsplit(".", 1)[0].strip()
                parts = name.split()

                if len(parts) < 4:
                    raise ValueError("Formato non valido")

                last_name = parts[0].strip()
                first_name = parts[1].strip()
                month_name = parts[2].strip().lower()
                year = int(parts[3])

                if month_name not in MONTHS_IT_REV:
                    raise ValueError("Mese non valido")

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

                existing = Payslip.objects.filter(
                    employee=employee,
                    year=year,
                    month=month
                ).first()

                if existing:
                    existing.pdf.name = pending_path
                    existing.save()
                else:
                    Payslip.objects.create(
                        employee=employee,
                        year=year,
                        month=month,
                        pdf=pending_path,
                    )

                report["saved_existing"] += 1

            except Exception:
                report["errors"] += 1

        messages.success(
            request,
            f"Import completato. Salvati: {report['saved_existing']}, "
            f"Nuovi non trovati: {report['new_found']}, "
            f"Errori: {report['errors']}"
        )

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

    if q:
        employees = employees.filter(full_name__icontains=q)

    return render(request, "portal/admin_manage_employees.html", {
        "employees": employees,
        "q": q
    })


# ==========================================================
# ✅ LISTA CEDOLINI DIPENDENTE
# ==========================================================
@login_required
def admin_employee_payslips(request, employee_id):
    if not request.user.is_staff:
        return redirect("home")

    employee = get_object_or_404(Employee, id=employee_id)
    payslips = Payslip.objects.filter(employee=employee).order_by("-year", "-month")

    return render(request, "portal/admin_employee_payslips.html", {
        "employee": employee,
        "payslips": payslips
    })


@login_required
def home(request):
    return render(request, "portal/home.html")


@login_required
def force_password_change_if_needed(request):
    return redirect("home")


# ==========================================================
# ✅ APERTURA PDF CEDOLINO (AGGIUNTO)
# ==========================================================
@login_required
def open_payslip(request, payslip_id):
    """
    Visualizza il PDF del cedolino.
    Gli admin possono vedere tutto, i dipendenti solo il proprio.
    """
    if request.user.is_staff:
        # Se è un admin, cerca il cedolino normalmente
        payslip = get_object_or_404(Payslip, id=payslip_id)
    else:
        # Se è un utente normale, lo trova solo se collegato al suo account Employee
        # Nota: assume che il modello Employee abbia un campo 'user'
        payslip = get_object_or_404(Payslip, id=payslip_id, employee__user=request.user)
    
    if not payslip.pdf:
        raise Http404("File PDF non associato a questo cedolino.")
        
    try:
        return FileResponse(payslip.pdf.open('rb'), content_type='application/pdf')
    except FileNotFoundError:
        raise Http404("Il file fisico non esiste sul server.")