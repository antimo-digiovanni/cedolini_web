import re
from typing import Optional, Tuple
from email.mime.image import MIMEImage

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.tokens import default_token_generator
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db.models import Count, ExpressionWrapper, F, IntegerField
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode

from .models import Employee, Payslip, PayslipView, AuditEvent

User = get_user_model()

MONTHS_IT = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
    5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
    9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre",
}
MONTHS_IT_REV = {v.lower(): k for k, v in MONTHS_IT.items()}


# ==========================================================
# ✅ Utils (IP, user-agent, audit, email html con logo CID)
# ==========================================================
def _client_ip(request) -> str:
    return (request.META.get("REMOTE_ADDR") or "").strip()


def _user_agent(request) -> str:
    return (request.META.get("HTTP_USER_AGENT") or "").strip()


def _audit(request, *, action: str, employee: Employee = None, payslip: Payslip = None, metadata: dict = None):
    try:
        AuditEvent.objects.create(
            action=action,
            actor_user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
            employee=employee,
            payslip=payslip,
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            metadata=metadata or {},
        )
    except Exception:
        pass


def _attach_logo_cid(msg: EmailMultiAlternatives) -> None:
    logo_path = finders.find("portal/logo.png")
    if not logo_path:
        return
    try:
        with open(logo_path, "rb") as f:
            img = MIMEImage(f.read())
            img.add_header("Content-ID", "<logo_cid>")
            img.add_header("Content-Disposition", "inline", filename="logo.png")
            msg.attach(img)
    except Exception:
        pass


def _send_html_email_with_logo(*, subject: str, to_list: list, text_template: str, html_template: str, context: dict):
    if not to_list:
        return

    text_body = render_to_string(text_template, context)
    html_body = render_to_string(html_template, context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=to_list,
    )
    msg.attach_alternative(html_body, "text/html")
    _attach_logo_cid(msg)
    msg.send(fail_silently=True)


# ==========================================================
# ✅ Nome/Cognome (iniziale maiuscola)
# ==========================================================
def _nice_capitalization(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+", " ", value)
    if not value:
        return ""

    def cap_word(w: str) -> str:
        w = w.lower()
        parts = re.split(r"([\'\-])", w)
        out = []
        for p in parts:
            if p in ["'", "-"]:
                out.append(p)
            elif p:
                out.append(p[0].upper() + p[1:])
        return "".join(out)

    return " ".join(cap_word(w) for w in value.split(" "))


def _needs_profile(user) -> bool:
    return not ((user.first_name or "").strip() and (user.last_name or "").strip())


class CompleteProfileForm(forms.Form):
    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Cognome", max_length=150)

    def clean_first_name(self):
        return _nice_capitalization(self.cleaned_data["first_name"])

    def clean_last_name(self):
        return _nice_capitalization(self.cleaned_data["last_name"])


@login_required
def complete_profile(request):
    employee = Employee.objects.filter(user_id=request.user.id).first()
    if not employee:
        if request.user.is_staff or request.user.is_superuser:
            return redirect("admin_dashboard")
        return redirect("home")

    if request.method == "POST":
        form = CompleteProfileForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]

            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.save()

            employee.full_name = f"{first_name} {last_name}".strip()
            employee.save()

            messages.success(request, "Dati salvati correttamente.")
            return redirect("check_password")
    else:
        form = CompleteProfileForm(initial={
            "first_name": request.user.first_name or "",
            "last_name": request.user.last_name or "",
        })

    return render(request, "portal/complete_profile.html", {"form": form})


# ==========================================================
# ✅ Attivazione invito (se la usi)
# ==========================================================
class ActivateAccountForm(forms.Form):
    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Cognome", max_length=150)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput, min_length=1)
    password2 = forms.CharField(label="Conferma Password", widget=forms.PasswordInput, min_length=1)

    def clean_first_name(self):
        return _nice_capitalization(self.cleaned_data["first_name"])

    def clean_last_name(self):
        return _nice_capitalization(self.cleaned_data["last_name"])

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Le password non coincidono.")
        return cleaned


def activate_account(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "Link non valido o scaduto. Contatta l'amministrazione.")
        return redirect("login")

    employee = Employee.objects.filter(user_id=user.pk).first()

    if request.method == "POST":
        form = ActivateAccountForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            password = form.cleaned_data["password1"]

            user.first_name = first_name
            user.last_name = last_name
            user.set_password(password)
            user.save()

            if employee:
                employee.full_name = f"{first_name} {last_name}".strip()
                employee.must_change_password = False
                employee.save()

            messages.success(request, "Registrazione completata. Ora puoi accedere con username e password.")
            return redirect("login")
    else:
        form = ActivateAccountForm()

    return render(request, "portal/activate_account.html", {"form": form, "username": user.username, "email": user.email})


# ==========================================================
# ✅ Cambio password senza password attuale
# ==========================================================
@login_required
def portal_set_password(request):
    if request.method == "POST":
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            Employee.objects.filter(user_id=request.user.id).update(must_change_password=False)

            messages.success(request, "Password aggiornata correttamente.")
            if _needs_profile(request.user):
                return redirect("complete_profile")
            return redirect("password_change_done")
    else:
        form = SetPasswordForm(request.user)

    return render(request, "registration/password_set_form.html", {"form": form})


@login_required
def portal_set_password_done(request):
    return render(request, "registration/password_set_done.html")


# ==========================================================
# ✅ Login / Home / Dashboard
# ==========================================================
class LoginView(DjangoLoginView):
    template_name = "portal/login.html"

    def get_success_url(self):
        return reverse("check_password")


@login_required
def home(request):
    employee = Employee.objects.filter(user_id=request.user.id).first()

    if employee:
        payslips = Payslip.objects.filter(employee=employee).select_related("view").order_by("-year", "-month")
        for p in payslips:
            p.month_name = MONTHS_IT.get(p.month, str(p.month))
        return render(request, "portal/home.html", {"payslips": payslips})

    if request.user.is_staff or request.user.is_superuser:
        return redirect("admin_dashboard")

    messages.error(request, "Nessun profilo dipendente collegato a questo utente.")
    return redirect("login")


@login_required
def admin_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("home")

    total_payslips = Payslip.objects.count()
    viewed_payslips = Payslip.objects.filter(view__isnull=False).count()
    not_viewed_payslips = total_payslips - viewed_payslips

    return render(request, "portal/admin_dashboard.html", {
        "total_payslips": total_payslips,
        "viewed_payslips": viewed_payslips,
        "not_viewed_payslips": not_viewed_payslips,
    })


@login_required
def force_password_change_if_needed(request):
    employee = Employee.objects.filter(user_id=request.user.id).first()

    if employee:
        if _needs_profile(request.user):
            messages.info(request, "Completa Nome e Cognome per continuare.")
            return redirect("complete_profile")

        if employee.must_change_password:
            messages.warning(request, "Devi cambiare la password prima di continuare.")
            return redirect("password_change")

        return redirect("home")

    if request.user.is_staff or request.user.is_superuser:
        return redirect("admin_dashboard")

    return redirect("home")


# ==========================================================
# ✅ Email ADMIN: cedolino letto (professionale)
# ==========================================================
def _send_admin_payslip_viewed_email(*, employee: Employee, payslip: Payslip, viewed_at_dt):
    admin_email = getattr(settings, "ADMIN_NOTIFY_EMAIL", "") or ""
    if not admin_email:
        return

    month_name = MONTHS_IT.get(payslip.month, str(payslip.month))
    viewed_local = timezone.localtime(viewed_at_dt) if viewed_at_dt else timezone.localtime()
    viewed_at_str = viewed_local.strftime("%d/%m/%Y %H:%M:%S")

    user = employee.user
    context = {
        "employee_full_name": employee.full_name,
        "username": getattr(user, "username", ""),
        "employee_email": getattr(user, "email", ""),
        "month_name": month_name,
        "year": payslip.year,
        "viewed_at": viewed_at_str,
        "signature_name": "Antimo Di Giovanni",
    }

    subject = f"[Portale Cedolini] Letto: {employee.full_name} – {month_name} {payslip.year}"
    _send_html_email_with_logo(
        subject=subject,
        to_list=[admin_email],
        text_template="portal/emails/payslip_viewed.txt",
        html_template="portal/emails/payslip_viewed.html",
        context=context,
    )


# ==========================================================
# ✅ Email DIPENDENTE: UNA SOLA EMAIL PER MESE
# ==========================================================
def _send_employee_month_notification(employee: Employee, month: int, year: int):
    user = employee.user
    to_email = (getattr(user, "email", "") or "").strip()
    if not to_email:
        return

    month_name = MONTHS_IT.get(month, str(month))

    protocol = getattr(settings, "DEFAULT_PROTOCOL", "http")
    domain = getattr(settings, "DEFAULT_DOMAIN", "127.0.0.1:8000")
    portal_url = f"{protocol}://{domain}/login/"

    context = {
        "employee_full_name": employee.full_name,
        "username": getattr(user, "username", ""),
        "month_name": month_name,
        "year": year,
        "portal_url": portal_url,
        "signature_name": "Antimo Di Giovanni",
    }

    subject = f"[Portale Cedolini] Cedolino disponibile: {month_name} {year}"

    _send_html_email_with_logo(
        subject=subject,
        to_list=[to_email],
        text_template="portal/emails/month_notification.txt",
        html_template="portal/emails/month_notification.html",
        context=context,
    )


# ==========================================================
# ✅ Apertura cedolino (log + email admin)
# ==========================================================
@login_required
def open_payslip(request, payslip_id):
    employee = Employee.objects.filter(user_id=request.user.id).first()
    if employee is None:
        messages.error(request, "Accesso non consentito (utente non associato a dipendente).")
        if request.user.is_staff or request.user.is_superuser:
            return redirect("admin_dashboard")
        return redirect("home")

    payslip = get_object_or_404(Payslip, id=payslip_id, employee=employee)

    if not hasattr(payslip, "view"):
        view_obj = PayslipView.objects.create(payslip=payslip)

        _audit(
            request,
            action=AuditEvent.ACTION_VIEWED,
            employee=employee,
            payslip=payslip,
            metadata={"viewed_at": timezone.localtime(view_obj.viewed_at).isoformat()},
        )

        _send_admin_payslip_viewed_email(employee=employee, payslip=payslip, viewed_at_dt=view_obj.viewed_at)

    return redirect(payslip.pdf.url)


# ==========================================================
# ✅ Report admin
# ==========================================================
@login_required
def admin_report(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("home")

    total_payslips = Payslip.objects.count()
    viewed_payslips = Payslip.objects.filter(view__isnull=False).count()
    not_viewed_payslips = total_payslips - viewed_payslips

    per_employee = (
        Employee.objects
        .annotate(total=Count("payslips"))
        .annotate(viewed=Count("payslips__view"))
        .annotate(not_viewed=ExpressionWrapper(F("total") - F("viewed"), output_field=IntegerField()))
        .order_by("full_name", "external_code", "id")
    )

    return render(request, "portal/admin_report.html", {
        "total_payslips": total_payslips,
        "viewed_payslips": viewed_payslips,
        "not_viewed_payslips": not_viewed_payslips,
        "per_employee": per_employee,
    })


# ==========================================================
# ✅ Dashboard audit (punto 4)
# ==========================================================
@login_required
def admin_audit_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("home")

    action = (request.GET.get("action") or "").strip()
    q = (request.GET.get("q") or "").strip()

    qs = AuditEvent.objects.select_related("employee", "payslip", "actor_user").all()

    if action:
        qs = qs.filter(action=action)

    if q:
        qs = qs.filter(
            employee__full_name__icontains=q
        ) | qs.filter(
            actor_user__username__icontains=q
        ) | qs.filter(
            ip_address__icontains=q
        )

    paginator = Paginator(qs.order_by("-created_at"), 50)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    totals = {
        "viewed": AuditEvent.objects.filter(action=AuditEvent.ACTION_VIEWED).count(),
        "uploaded": AuditEvent.objects.filter(action=AuditEvent.ACTION_UPLOADED).count(),
        "updated": AuditEvent.objects.filter(action=AuditEvent.ACTION_UPDATED).count(),
        "deleted": AuditEvent.objects.filter(action=AuditEvent.ACTION_DELETED).count(),
        "reset_view": AuditEvent.objects.filter(action=AuditEvent.ACTION_RESET_VIEW).count(),
    }

    return render(request, "portal/admin_audit_dashboard.html", {
        "page_obj": page_obj,
        "action": action,
        "q": q,
        "totals": totals,
        "actions": AuditEvent.ACTION_CHOICES,
    })


# ==========================================================
# ✅ Upload singolo (email unica per mese)
# ==========================================================
class AdminUploadPayslipForm(forms.Form):
    employee = forms.ModelChoiceField(queryset=Employee.objects.order_by("full_name", "external_code", "id"))
    month = forms.ChoiceField(choices=[(i, MONTHS_IT[i]) for i in range(1, 13)])
    year = forms.IntegerField(min_value=2000, max_value=2100)
    pdf = forms.FileField()


@login_required
def admin_upload_payslip(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("home")

    if request.method == "POST":
        form = AdminUploadPayslipForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.cleaned_data["employee"]
            month = int(form.cleaned_data["month"])
            year = int(form.cleaned_data["year"])
            pdf = form.cleaned_data["pdf"]

            existing = Payslip.objects.filter(employee=employee, year=year, month=month).first()

            if existing:
                try:
                    if existing.pdf:
                        existing.pdf.delete(save=False)
                except Exception:
                    pass

                existing.pdf = pdf
                existing.save()

                if hasattr(existing, "view"):
                    existing.view.delete()

                _audit(request, action=AuditEvent.ACTION_UPDATED, employee=employee, payslip=existing, metadata={"source": "single"})
                messages.success(request, "Cedolino aggiornato.")
            else:
                created = Payslip.objects.create(employee=employee, year=year, month=month, pdf=pdf)
                _audit(request, action=AuditEvent.ACTION_UPLOADED, employee=employee, payslip=created, metadata={"source": "single"})
                messages.success(request, "Cedolino caricato.")

            _send_employee_month_notification(employee, month, year)
            messages.success(request, "Email mensile inviata al dipendente (se presente).")

            return redirect("admin_upload_payslip")
    else:
        form = AdminUploadPayslipForm()

    return render(request, "portal/admin_upload.html", {"form": form})


# ==========================================================
# ✅ Import mese (email unica per mese, una per dipendente)
# ==========================================================
_SUFFIX_RE = re.compile(r"^(?P<name>.+?)_(?P<idx>\d{1,3})$", re.UNICODE)

def _normalize_spaces(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def _parse_employee_folder(folder_name: str) -> Optional[Tuple[str, Optional[int]]]:
    folder_name = _normalize_spaces(folder_name)
    if not folder_name:
        return None
    m = _SUFFIX_RE.match(folder_name)
    if m:
        base = _normalize_spaces(m.group("name"))
        idx = int(m.group("idx"))
        return base, idx
    return folder_name, None

def _code_from_idx(idx: int) -> str:
    if idx is None:
        return ""
    return str(int(idx)).zfill(2)

def _find_employee(base_name: str, idx: Optional[int]) -> Optional[Employee]:
    base_name = _normalize_spaces(base_name)
    if not base_name:
        return None

    if idx is not None:
        code = _code_from_idx(idx)
        qs = Employee.objects.filter(full_name__iexact=base_name, external_code=code).order_by("id")
        if qs.exists():
            return qs.first()
        qs = Employee.objects.filter(full_name__istartswith=base_name, external_code=code).order_by("id")
        if qs.exists():
            return qs.first()
        qs = Employee.objects.filter(full_name__icontains=base_name, external_code=code).order_by("id")
        if qs.exists():
            return qs.first()
        return None

    qs = Employee.objects.filter(full_name__iexact=base_name).order_by("id")
    return qs.first() if qs.exists() else None

def _employee_from_anything(raw_path: str) -> Optional[Employee]:
    raw = (raw_path or "").replace("\\", "/").strip()
    if not raw:
        return None
    parts = [p for p in raw.split("/") if p.strip()]
    filename = parts[-1] if parts else raw

    if len(parts) >= 2:
        pe = _parse_employee_folder(parts[-2])
        if pe:
            base, idx = pe
            emp = _find_employee(base, idx)
            if emp:
                return emp

    basefile = filename.rsplit(".", 1)[0].strip()
    pe = _parse_employee_folder(basefile)
    if not pe:
        return None
    base, idx = pe
    return _find_employee(base, idx)


@login_required
def admin_upload_period_folder(request):
    if not (request.user.is_staff or request.user.is_superuser):
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

        import uuid, os
        batch_id = str(uuid.uuid4())
        pending_dir = os.path.join(settings.PENDING_UPLOAD_DIR, batch_id)
        os.makedirs(pending_dir, exist_ok=True)

        new_employees = []

        for f in files:
            try:
                pending_path = os.path.join(pending_dir, f.name)

                with open(pending_path, "wb+") as destination:
                    for chunk in f.chunks():
                        destination.write(chunk)

                name = f.name.rsplit(".", 1)[0].strip()
parts = name.split()

if len(parts) < 4:
    raise ValueError("Formato non valido. Usa: COGNOME NOME MESE ANNO.pdf")

last_name = parts[0].strip()
first_name = parts[1].strip()
month_name = parts[2].strip().lower()
year = int(parts[3])

if month_name not in MONTHS_IT_REV:
    raise ValueError("Mese non valido")

month = MONTHS_IT_REV[month_name]

                full_name = f"{first_name} {last_name}".strip()
                employee = Employee.objects.filter(full_name__iexact=full_name).first()

                # Se esiste già → salva direttamente
                if employee:
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

                # Se NON esiste → metti in lista conferma
                else:
                    new_employees.append({
                        "first_name": first_name,
                        "last_name": last_name,
                        "month": month,
                        "year": year,
                        "file_path": pending_path,
                    })
                    report["new_found"] += 1

            except Exception:
                report["errors"] += 1

        request.session["pending_batch"] = batch_id
        request.session["pending_new_employees"] = new_employees

        if new_employees:
            return redirect("admin_confirm_import")

        messages.success(
            request,
            f"Import completato. Salvati: {report['saved_existing']}, Errori: {report['errors']}"
        )

        return render(request, "portal/admin_upload_period_folder.html", {"report": report})

    return render(request, "portal/admin_upload_period_folder.html", {"report": report})


@login_required
def admin_employee_payslips(request, employee_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("home")

    employee = get_object_or_404(Employee, id=employee_id)
    payslips = Payslip.objects.filter(employee=employee).select_related("view").order_by("-year", "-month", "-uploaded_at")
    for p in payslips:
        p.month_name = MONTHS_IT.get(p.month, str(p.month))

    return render(request, "portal/admin_employee_payslips.html", {"employee": employee, "payslips": payslips})


@login_required
def admin_reset_payslip_view(request, payslip_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("home")

    payslip = get_object_or_404(Payslip, id=payslip_id)
    employee = payslip.employee
    employee_id = payslip.employee_id

    if request.method == "POST":
        if hasattr(payslip, "view"):
            payslip.view.delete()
            _audit(request, action=AuditEvent.ACTION_RESET_VIEW, employee=employee, payslip=payslip)
            messages.success(request, "Visualizzazione resettata.")
        else:
            messages.info(request, "Il cedolino non risultava visualizzato.")

    return redirect("admin_employee_payslips", employee_id=employee_id)


@login_required
def admin_delete_payslip(request, payslip_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("home")

    payslip = get_object_or_404(Payslip, id=payslip_id)
    employee = payslip.employee
    employee_id = payslip.employee_id

    if request.method == "GET":
        return render(request, "portal/admin_confirm_delete_payslip.html", {"payslip": payslip})

    try:
        if payslip.pdf:
            payslip.pdf.delete(save=False)
    except Exception:
        pass

    _audit(request, action=AuditEvent.ACTION_DELETED, employee=employee, payslip=payslip)
    payslip.delete()
    messages.success(request, "Cedolino cancellato.")
    return redirect("admin_employee_payslips", employee_id=employee_id)

# ==========================================================
# ✅ Gestione cedolini (delete/reset view)
# ==========================================================

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Employee

@login_required
def admin_manage_employees(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("home")

    q = (request.GET.get("q") or "").strip()
    employees = Employee.objects.all().order_by("full_name", "id")

    if q:
        employees = employees.filter(full_name__icontains=q)

    return render(request, "portal/admin_manage_employees.html", {
        "employees": employees,
        "q": q
    })