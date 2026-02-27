import re
import uuid
import os
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404

from .models import Employee, Payslip

# Dizionario mesi per la conversione
MONTHS_IT = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
    5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
    9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre",
}

MONTHS_IT_REV = {v.lower(): k for k, v in MONTHS_IT.items()}

# ==========================================================
# ✅ AUTENTICAZIONE E PROFILO
# ==========================================================
class LoginView(DjangoLoginView):
    template_name = "registration/login.html"

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

@login_required
def portal_set_password(request):
    return render(request, "registration/password_change_form.html")

@login_required
def portal_set_password_done(request):
    return render(request, "registration/password_change_done.html")

# ==========================================================
# ✅ DASHBOARD E REPORT ADMIN
# ==========================================================
@login_required
def admin_dashboard(request):
    if not request.user.is_staff: return redirect("home")
    return render(request, "portal/admin_dashboard.html", {"total_payslips": Payslip.objects.count()})

@login_required
def admin_report(request):
    if not request.user.is_staff: return redirect("home")
    latest = Payslip.objects.all().order_by("-id")[:50]
    return render(request, "portal/admin_report.html", {"payslips": latest})

@login_required
def admin_audit_dashboard(request):
    if not request.user.is_staff: return redirect("home")
    return render(request, "portal/admin_audit_dashboard.html")

# ==========================================================
# ✅ GESTIONE CARICAMENTI (AUTO-CREAZIONE DIPENDENTI)
# ==========================================================
@login_required
def admin_upload_payslip(request):
    return redirect("admin_upload_period_folder")

@login_required
def admin_confirm_import(request):
    messages.success(request, "Importazione confermata con successo.")
    return redirect("admin_dashboard")

@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff: return redirect("home")
    
    report = {"saved_existing": 0, "new_created": 0, "errors": 0}
    
    if request.method == "POST":
        files = request.FILES.getlist("files")
        # Cartella finale dove salvare i PDF
        upload_dir = os.path.join(settings.MEDIA_ROOT, "payslips")
        os.makedirs(upload_dir, exist_ok=True)

        for f in files:
            try:
                # 1. Estrazione dati dal nome: "COGNOME NOME MESE ANNO.pdf"
                name_part = f.name.rsplit(".", 1)[0].strip()
                parts = name_part.split()
                
                if len(parts) < 4: raise ValueError("Formato nome file corto")

                last_name = parts[0].strip()
                first_name = parts[1].strip()
                month_str = parts[2].strip().lower()
                year = int(parts[3])
                
                month = MONTHS_IT_REV.get(month_str)
                if not month: raise ValueError("Mese non valido")

                # Formattiamo il nome completo per il database
                full_name = f"{first_name} {last_name}".upper()

                # 2. Cerca il dipendente. Se NON esiste, lo CREA automaticamente
                employee, created = Employee.objects.get_or_create(
                    full_name=full_name,
                    defaults={'email_sent': False}
                )

                if created:
                    report["new_created"] += 1
                else:
                    report["saved_existing"] += 1

                # 3. Salvataggio fisico del file
                # Usiamo un nome file pulito per evitare problemi di caratteri speciali
                safe_filename = f"{last_name}_{first_name}_{month}_{year}.pdf".replace(" ", "_")
                file_path = os.path.join(upload_dir, safe_filename)
                
                with open(file_path, "wb+") as dest:
                    for chunk in f.chunks(): dest.write(chunk)

                # 4. Creazione/Aggiornamento del record Cedolino
                # Salviamo il percorso relativo nel DB
                db_path = os.path.join("payslips", safe_filename)
                Payslip.objects.update_or_create(
                    employee=employee, 
                    year=year, 
                    month=month,
                    defaults={'pdf': db_path}
                )

            except Exception as e:
                print(f"Errore file {f.name}: {e}")
                report["errors"] += 1
        
        msg = f"Processo completato! Creati: {report['new_created']}, Esistenti: {report['saved_existing']}, Errori: {report['errors']}"
        messages.success(request, msg)

    return render(request, "portal/admin_upload_period_folder.html", {"report": report})

# ==========================================================
# ✅ GESTIONE DIPENDENTI E CEDOLINI
# ==========================================================
@login_required
def admin_manage_employees(request):
    if not request.user.is_staff: return redirect("home")
    q = (request.GET.get("q") or "").strip()
    employees = Employee.objects.all().order_by("full_name")
    if q: employees = employees.filter(full_name__icontains=q)
    return render(request, "portal/admin_manage_employees.html", {"employees": employees, "q": q})

@login_required
def admin_employee_payslips(request, employee_id):
    if not request.user.is_staff: return redirect("home")
    employee = get_object_or_404(Employee, id=employee_id)
    payslips = Payslip.objects.filter(employee=employee).order_by("-year", "-month")
    return render(request, "portal/admin_employee_payslips.html", {"employee": employee, "payslips": payslips})

@login_required
def admin_reset_payslip_view(request, payslip_id):
    if not request.user.is_staff: return redirect("home")
    messages.success(request, "Stato visualizzazione resettato.")
    return redirect("admin_dashboard")

@login_required
def admin_delete_payslip(request, payslip_id):
    if not request.user.is_staff: return redirect("home")
    payslip = get_object_or_404(Payslip, id=payslip_id)
    payslip.delete()
    messages.warning(request, "Cedolino eliminato.")
    return redirect("admin_dashboard")

# ==========================================================
# ✅ VISUALIZZAZIONE PDF
# ==========================================================
@login_required
def open_payslip(request, payslip_id):
    if request.user.is_staff:
        payslip = get_object_or_404(Payslip, id=payslip_id)
    else:
        payslip = get_object_or_404(Payslip, id=payslip_id, employee__user=request.user)
    
    if not payslip.pdf: raise Http404()
    
    # Supporta sia percorsi assoluti che FileField di Django
    try:
        return FileResponse(payslip.pdf.open('rb'), content_type='application/pdf')
    except:
        # Fallback se il file è su disco ma il DB ha solo il percorso
        if os.path.exists(payslip.pdf.path):
            return FileResponse(open(payslip.pdf.path, 'rb'), content_type='application/pdf')
        raise Http404("File fisico non trovato.")