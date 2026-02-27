# ==========================================================
# =====================  IMPORT CON CONFERMA  ===============
# ==========================================================

import os
import uuid
from django.contrib.auth.decorators import login_required


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

                name = f.name.rsplit(".", 1)[0]
                parts = re.split(r"\s*[-–—]\s*", name)

                if len(parts) < 3:
                    raise ValueError("Formato non valido")

                last_name = parts[0].strip()
                first_name = parts[1].strip()
                month_year = parts[2].strip()

                m = re.match(
                    r"^(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})$",
                    month_year,
                    flags=re.IGNORECASE,
                )
                if not m:
                    raise ValueError("Mese/anno non valido")

                month = MONTHS_IT_REV[m.group(1).lower()]
                year = int(m.group(2))

                full_name = f"{first_name} {last_name}".strip()
                employee = Employee.objects.filter(full_name__iexact=full_name).first()

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
def admin_confirm_import(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("home")

    batch_id = request.session.get("pending_batch")
    new_employees = request.session.get("pending_new_employees", [])

    if not batch_id or not new_employees:
        return redirect("admin_upload_period_folder")

    pending_dir = os.path.join(settings.PENDING_UPLOAD_DIR, batch_id)

    if request.method == "POST":
        selected = request.POST.getlist("create_employee")

        for idx, data in enumerate(new_employees):
            file_path = data["file_path"]

            if str(idx) in selected:
                first_name = data["first_name"]
                last_name = data["last_name"]
                month = data["month"]
                year = data["year"]

                full_name = f"{first_name} {last_name}".strip()

                base_username = re.sub(
                    r"[^a-z0-9]+",
                    "_",
                    f"{first_name}_{last_name}".lower()
                ).strip("_")

                username = base_username
                i = 1
                while User.objects.filter(username=username).exists():
                    i += 1
                    username = f"{base_username}_{i}"

                user = User.objects.create(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False,
                )
                user.set_unusable_password()
                user.save()

                employee = Employee.objects.create(
                    user=user,
                    full_name=full_name,
                    must_change_password=True,
                )

                Payslip.objects.create(
                    employee=employee,
                    year=year,
                    month=month,
                    pdf=file_path,
                )

                _send_employee_month_notification(employee, month, year)

            else:
                if os.path.exists(file_path):
                    os.remove(file_path)

        if os.path.exists(pending_dir):
            try:
                os.rmdir(pending_dir)
            except:
                pass

        request.session.pop("pending_batch", None)
        request.session.pop("pending_new_employees", None)

        messages.success(request, "Import completato.")
        return redirect("admin_upload_period_folder")

    return render(request, "portal/admin_confirm_import.html", {
        "new_employees": new_employees
    })