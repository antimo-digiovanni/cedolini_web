import os
import re
import unicodedata
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from portal.models import Employee, Payslip


def slugify_username(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace(" ", "_").replace("'", "_")


MONTHS_IT = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}


FILENAME_RE = re.compile(
    r"^\s*(?P<name>.+?)\s+(?P<month>Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre)\s+(?P<year>\d{4})\s*\.pdf\s*$",
    re.IGNORECASE,
)


class Command(BaseCommand):
    help = "Importa cedolini PDF da una cartella (ricorsivo)."

    def add_arguments(self, parser):
        parser.add_argument("folder", type=str)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        folder = options["folder"]
        dry_run = options["dry_run"]

        base = Path(folder)
        if not base.exists() or not base.is_dir():
            raise CommandError(f"Cartella non valida: {folder}")

        pdf_paths = sorted(base.rglob("*.pdf"))
        if not pdf_paths:
            self.stdout.write(self.style.WARNING("Nessun PDF trovato."))
            return

        User = get_user_model()

        employees_created = 0
        payslips_created = 0
        skipped = 0

        ctx = transaction.atomic() if not dry_run else _DummyContext()

        with ctx:
            for pdf_path in pdf_paths:
                filename = pdf_path.name

                m = FILENAME_RE.match(filename)
                if not m:
                    skipped += 1
                    continue

                full_name = m.group("name").strip()
                month_name = m.group("month").strip().lower()
                year = int(m.group("year"))

                month = MONTHS_IT.get(month_name)
                if not month:
                    skipped += 1
                    continue

                username = slugify_username(full_name)

                if not dry_run:
                    user, user_created = User.objects.get_or_create(
                        username=username,
                        defaults={"is_active": True},
                    )

                    employee, emp_created = Employee.objects.get_or_create(
                        user=user,
                        defaults={"full_name": full_name},
                    )

                    if employee.full_name != full_name:
                        employee.full_name = full_name
                        employee.save(update_fields=["full_name"])

                    # 🔹 PASSWORD TEMPORANEA + OBBLIGO CAMBIO
                    if user_created:
                        user.set_password("cambiala2026")
                        user.save(update_fields=["password"])

                        employee.must_change_password = True
                        employee.save(update_fields=["must_change_password"])

                    if emp_created:
                        employees_created += 1

                    exists = Payslip.objects.filter(
                        employee=employee,
                        year=year,
                        month=month
                    ).exists()

                    if exists:
                        skipped += 1
                        continue

                    with open(pdf_path, "rb") as f:
                        payslip = Payslip(
                            employee=employee,
                            year=year,
                            month=month
                        )
                        payslip.pdf.save(pdf_path.name, File(f), save=True)

                    payslips_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"FINE. Employees creati: {employees_created}, Payslips creati: {payslips_created}, Skippati: {skipped}"
            )
        )


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False