import os
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404
from django.core.mail import send_mail
from .models import Employee, Payslip

# Dizionario per convertire i mesi dal nome del file
MONTHS_REV = {
    "gennaio":1, "febbraio":2, "marzo":3, "aprile":4, "maggio":5, "giugno":6,
    "luglio":7, "agosto":8, "settembre":9, "ottobre":10, "novembre":11, "dicembre":12
}

# ✅ LoginView richiesta da urls.py
class LoginView(DjangoLoginView):
    template_name = "registration/login.html"

@login_required
def home(request):
    # Forza il cambio password se l'utente è un dipendente e ha ancora 'cambiala'
    try:
        if not request.user.is_staff and (request.user.check_password("cambiala") or request.user.employee.must_change_password):
            return redirect("password_change")
    except: pass
    return render(request, "portal/home.html")

@login_required
def admin_upload_period_folder(request):
    """Caricamento massivo PDF: Crea Utente (nome-cognome) e Employee"""
    if not request.user.is_staff: return redirect("home")
    
    if request.method == "POST":
        files = request.FILES.getlist("files")
        for f in files:
            try:
                # Parsing: 'COGNOME NOME MESE ANNO.pdf'
                p = f.name.rsplit(".", 1)[0].split()
                ln, fn, mo, yr = p[0].upper(), p[1].upper(), MONTHS_REV[p[2].lower()], p[3]
                
                # 1. Creazione Utente Django (username: nome-cognome)
                uname = f"{fn.lower()}-{ln.lower()}"
                user, created = User.objects.get_or_create(
                    username=uname, 
                    defaults={'first_name': fn, 'last_name': ln, 'is_active': True}
                )
                if created:
                    user.set_password("cambiala")
                    user.save()

                # 2. Creazione/Aggiornamento Profilo Employee
                emp, _ = Employee.objects.get_or_create(
                    user=user, 
                    defaults={'full_name': f"{fn} {ln}", 'must_change_password': True}
                )
                
                # 3. Salvataggio PDF fisico
                fname = f"{ln}_{fn}_{mo}_{yr}.pdf".replace(" ", "_")
                fpath = os.path.join(settings.MEDIA_ROOT, "payslips", fname)
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "wb+") as d:
                    for c in f.chunks(): d.write(c)

                # 4. Registrazione Cedolino nel DB
                Payslip.objects.update_or_create(
                    employee=emp, year=yr, month=mo, 
                    defaults={'pdf': f"payslips/{fname}"}
                )
            except Exception as e:
                print(f"Errore file {f.name}: {e}")
                continue
        messages.success(request, "Importazione completata con successo.")
    return render(request, "portal/admin_upload_period_folder.html")

@login_required
def admin_manage_employees(request):
    """Gestione anagrafica: inserendo la mail invia l'invito automatico"""
    if not request.user.is_staff: return redirect("home")
    
    if request.method == "POST":
        emp = get_object_or_404(Employee, id=request.POST.get("emp_id"))
        email = request.POST.get("email")
        
        if email:
            emp.user.email = email
            emp.user.save()
            
            # Invio Email con parametri Aruba SSL
            try:
                site_url = request.build_absolute_uri('/')
                send_mail(
                    "Benvenuto nel Portale Cedolini - San Vincenzo",
                    f"Ciao {emp.user.first_name},\n\nIl tuo account è pronto.\nUsername: {emp.user.username}\nPassword temporanea: cambiala\n\nAccedi qui: {site_url}\n\nNota: Ti verrà chiesto di cambiare la password al primo accesso.",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, f"Invito inviato correttamente a {email}")
            except Exception as e:
                messages.error(request, f"Errore invio mail (SMTP Aruba): {e}")
    
    q = request.GET.get("q", "")
    emps = Employee.objects.filter(full_name__icontains=q).order_by('full_name') if q else Employee.objects.all().order_by('full_name')
    return render(request, "portal/admin_manage_employees.html", {"employees": emps, "q": q})

@login_required
def open_payslip(request, payslip_id):
    """Apre il PDF del cedolino"""
    if request.user.is_staff:
        ps = get_object_or_404(Payslip, id=payslip_id)
    else:
        ps = get_object_or_404(Payslip, id=payslip_id, employee__user=request.user)
    return FileResponse(ps.pdf.open('rb'), content_type='application/pdf')

@login_required
def portal_set_password(request):
    """Resetta il flag di cambio password obbligatorio dopo il cambio"""
    if request.method == "POST":
        # Il form di Django gestisce il cambio, noi segniamo il completamento
        request.user.employee.must_change_password = False
        request.user.employee.save()
    return render(request, "registration/password_change_form.html")

# --- Supporto per URLS.PY (funzioni richieste ma semplificate) ---
@login_required
def admin_dashboard(request): 
    return render(request, "portal/admin_dashboard.html", {"total_payslips": Payslip.objects.count()})

@login_required
def admin_report(request): 
    return render(request, "portal/admin_report.html", {"payslips": Payslip.objects.all().order_by('-uploaded_at')[:50]})

@login_required
def admin_employee_payslips(request, employee_id): 
    e = get_object_or_404(Employee, id=employee_id)
    return render(request, "portal/admin_employee_payslips.html", {"employee": e, "payslips": e.payslips.all()})

@login_required
def admin_delete_payslip(request, payslip_id): 
    Payslip.objects.filter(id=payslip_id).delete()
    return redirect("admin_dashboard")

@login_required
def admin_audit_dashboard(request): return render(request, "portal/admin_audit_dashboard.html")
@login_required
def admin_upload_payslip(request): return redirect("admin_upload_period_folder")
@login_required
def admin_confirm_import(request): return redirect("admin_dashboard")
def activate_account(request, uidb64, token): return redirect("login")
def complete_profile(request): return redirect("home")
def force_password_change_if_needed(request): return redirect("home")
@login_required
def portal_set_password_done(request): return render(request, "registration/password_change_done.html")
@login_required
def admin_reset_payslip_view(request, payslip_id): return redirect("admin_dashboard")