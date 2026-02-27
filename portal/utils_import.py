import os
import re
import unicodedata

from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Employee, Payslip, AuditEvent

User = get_user_model()

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


def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _slug_ascii(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def parse_payslip_filename(filename: str):
    """
    Formato atteso:
      'COGNOME - NOME - MESE ANNO.pdf'
    Esempio:
      'Di Giovanni - Antimo - Gennaio 2026.pdf'
      'De Luca – Anna Maria – Febbraio 2026.pdf'
    Ritorna: (first_name, last_name, month_int, year_int)
    """
    base = os.path.splitext(os.path.basename(filename))[0]
    base = _norm_spaces(base)

    # Split su trattini: "-", "–", "—" con spazi opzionali
    parts = re.split(r"\s*[-–—]\s*", base)
    parts = [_norm_spaces(p) for p in parts if _norm_spaces(p)]

    if len(parts) < 3:
        raise ValueError("Formato non valido. Atteso: 'COGNOME - NOME - MESE ANNO'")

    last_name = parts[0]
    first_name = parts[1]
    mese_anno = parts[2]

    m = re.match(
        r"^(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})$",
        mese_anno,
        flags=re.IGNORECASE,
    )
    if not m:
        raise ValueError("Parte MESE ANNO non valida. Esempio: 'Gennaio 2026'")

    month = MONTHS_IT[m.group(1).lower()]
    year = int(m.group(2))

    if not first_name or not last_name:
        raise ValueError("Nome o cognome mancanti nel nome file")

    return first_name, last_name, month, year


def _make_username(first_name: str, last_name: str) -> str:
    base = _slug_ascii(f"{first_name}_{last_name}") if last_name else _slug_ascii(first_name)
    return (base or "user")[:150]


@transaction.atomic
def get_or_create_employee_from_name(first_name: str, last_name: str):
    """
    Ritorna (employee, created_bool)
    Strategia:
    - se esiste Employee con full_name == 'NOME COGNOME' (case-insensitive), usa quello
    - altrimenti crea User + Employee
    """
    full_name = _norm_spaces(f"{first_name} {last_name}")

    existing = Employee.objects.filter(full_name__iexact=full_name).select_related("user").first()
    if existing:
        return existing, False

    # Crea user con username univoco
    base_username = _make_username(first_name, last_name)
    username = base_username
    i = 1
    while User.objects.filter(username=username).exists():
        i += 1
        username = f"{base_username}_{i}"

    user = User.objects.create(
        username=username,
        first_name=first_name,
        last_name=last_name,
        is_active=False,  # si attiva quando accetta invito
    )
    user.set_unusable_password()
    user.save()

    emp = Employee.objects.create(user=user, full_name=full_name, must_change_password=True)
    return emp, True


@transaction.atomic
def import_payslips(files, actor_user=None, request_meta=None):
    """
    files: lista di UploadedFile
    actor_user: chi importa (admin)
    request_meta: dict con ip/user_agent ecc (opzionale)

    Ritorna report dict.
    """
    report = {
        "employees_created": 0,
        "payslips_created": 0,
        "payslips_updated": 0,
        "errors": [],
    }

    request_meta = request_meta or {}

    for f in files:
        try:
            first_name, last_name, month, year = parse_payslip_filename(getattr(f, "name", ""))
            employee, created_emp = get_or_create_employee_from_name(first_name, last_name)
            if created_emp:
                report["employees_created"] += 1

            obj, created = Payslip.objects.update_or_create(
                employee=employee,
                year=year,
                month=month,
                defaults={"pdf": f},
            )

            if created:
                report["payslips_created"] += 1
                action = AuditEvent.ACTION_UPLOADED
            else:
                report["payslips_updated"] += 1
                action = AuditEvent.ACTION_UPDATED

            AuditEvent.objects.create(
                action=action,
                actor_user=actor_user,
                employee=employee,
                payslip=obj,
                ip_address=request_meta.get("ip"),
                user_agent=request_meta.get("ua"),
                metadata={"source": "bulk_import"},
            )

        except Exception as e:
            report["errors"].append({"file": getattr(f, "name", "?"), "error": str(e)})

    return report