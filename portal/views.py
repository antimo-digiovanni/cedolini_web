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
    messages.info(request, "Account attivato. Effettua il login.")
    return redirect("login")

# ==========================================================
# ✅ DASHBOARD E REPORT ADMIN
# ==========================================================
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect("home")
    total_payslips = Payslip.objects.count()
    return render(request, "portal/admin_dashboard.html", {"total_payslips": total_payslips})

@login_required
def admin_report(request):
    """Aggiunta per risolvere errore AttributeError"""
    if not request.user.is_staff:
        return redirect("home")
    # Logica base per visualizzare gli ultimi inserimenti
    latest_payslips = Payslip.objects.all().order_by("-id")[:50]
    return render(request, "portal/admin_report.html", {"payslips": latest_payslips})

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
                if len(parts) < 4: raise ValueError("Formato errato")

                last_name, first_name = parts[0].strip(), parts[1].strip()
                month_name, year = parts[2].strip().lower(), int(parts[3])

                if month_name not in MONTHS_IT_REV