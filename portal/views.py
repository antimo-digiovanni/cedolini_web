import os
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404
from django.core.mail import send_mail
from .models import Employee, Payslip

MONTHS_REV = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12}

@login_required
def home(request):
    if not request.user.is_staff and request.user.check_password("cambiala"):
        return render(request, "registration/password_change_form.html", {"must_change": True})
    return render(request, "portal/home.html")

@login_required
def admin_upload_period_folder(request):
    if not request.user.is_staff: return redirect("home")
    if request.method == "POST":
        for f in request.FILES.getlist("files"):
            try:
                p = f.name.rsplit(".", 1)[0].split()
                ln, fn, mo, yr = p[0].upper(), p[1].upper(), MONTHS_REV[p[2].lower()], p[3]
                
                user, _ = User.objects.get_or_create(
                    username=f"{fn.lower()}-{ln.lower()}",
                    defaults={'first_name': fn, 'last_name': ln, 'is_active': True}
                )
                if _: user.set_password("cambiala"); user.save()

                emp, _ = Employee.objects.get_or_create(full_name=f"{fn} {ln}", defaults={'user': user})
                
                fname = f"{ln}_{fn}_{mo}_{yr}.pdf"
                fpath = os.path.join(settings.MEDIA_ROOT, "payslips", fname)
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "wb+") as d:
                    for c in f.chunks(): d.write(c)

                Payslip.objects.update_or_create(employee=emp, year=yr, month=mo, defaults={'pdf': f"payslips/{fname}"})
            except: continue
        messages.success(request, "Caricamento completato.")
    return render(request, "portal/admin_upload_period_folder.html")

@login_required
def admin_manage_employees(request):
    if not request.user.is_staff: return redirect("home")
    if request.method == "POST":
        emp = get_object_or_404(Employee, id=request.POST.get("emp_id"))
        email = request.POST.get("email")
        if email and not emp.user.email:
            emp.user.email = email
            emp.user.save()
            send_mail("Invito Portale", f"User: {emp.user.username}\nPass: cambiala", settings.DEFAULT_FROM_EMAIL, [email])
            messages.success(request, f"Invito inviato a {email}")
    
    q = request.GET.get("q", "")
    emps = Employee.objects.filter(full_name__icontains=q) if q else Employee.objects.all()
    return render(request, "portal/admin_manage_employees.html", {"employees": emps})

@login_required
def open_payslip(request, payslip_id):
    ps = get_object_or_404(Payslip, id=payslip_id) if request.user.is_staff else get_object_or_404(Payslip, id=payslip_id, employee__user=request.user)
    return FileResponse(ps.pdf.open('rb'), content_type='application/pdf')

# Funzioni placeholder per evitare errori urls.py
@login_required
def admin_dashboard(request): return render(request, "portal/admin_dashboard.html")
@login_required
def admin_report(request): return render(request, "portal/admin_report.html", {"payslips": Payslip.objects.all()[:50]})
@login_required
def admin_audit_dashboard(request): return render(request, "portal/admin_audit_dashboard.html")
@login_required
def admin_upload_payslip(request): return redirect("admin_upload_period_folder")
@login_required
def admin_confirm_import(request): return redirect("admin_dashboard")
@login_required
def admin_employee_payslips(request, employee_id): return render(request, "portal/admin_employee_payslips.html", {"employee": get_object_or_404(Employee, id=employee_id), "payslips": Payslip.objects.filter(employee_id=employee_id)})
@login_required
def admin_reset_payslip_view(request, payslip_id): return redirect("admin_dashboard")
@login_required
def admin_delete_payslip(request, payslip_id): Payslip.objects.filter(id=payslip_id).delete(); return redirect("admin_dashboard")
def activate_account(request, uidb64, token): return redirect("login")
def complete_profile(request): return redirect("home")
def force_password_change_if_needed(request): return redirect("home")
@login_required
def portal_set_password(request): return render(request, "registration/password_change_form.html")
@login_required
def portal_set_password_done(request): return render(request, "registration/password_change_done.html")