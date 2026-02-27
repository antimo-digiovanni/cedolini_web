from django.conf import settings
from django.db import models


class Employee(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=160)

    # ✅ per omonimi / _02 ecc.
    external_code = models.CharField(max_length=10, blank=True, null=True)

    must_change_password = models.BooleanField(default=True)

    def __str__(self):
        if self.external_code:
            return f"{self.full_name} ({self.external_code})"
        return self.full_name


class Payslip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payslips")
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    pdf = models.FileField(upload_to="payslips/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("employee", "year", "month")]
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.employee} {self.month:02d}/{self.year}"


class PayslipView(models.Model):
    payslip = models.OneToOneField(Payslip, on_delete=models.CASCADE, related_name="view")
    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Viewed {self.payslip} at {self.viewed_at}"


class AuditEvent(models.Model):
    """
    ✅ Log audit permanente:
    - VIEWED: dipendente ha aperto il PDF
    - UPLOADED/UPDATED: admin ha caricato/aggiornato
    - DELETED: admin ha cancellato
    - RESET_VIEW: admin ha resettato visualizzazione
    """

    ACTION_VIEWED = "VIEWED"
    ACTION_UPLOADED = "UPLOADED"
    ACTION_UPDATED = "UPDATED"
    ACTION_DELETED = "DELETED"
    ACTION_RESET_VIEW = "RESET_VIEW"

    ACTION_CHOICES = [
        (ACTION_VIEWED, "Letto"),
        (ACTION_UPLOADED, "Caricato"),
        (ACTION_UPDATED, "Aggiornato"),
        (ACTION_DELETED, "Cancellato"),
        (ACTION_RESET_VIEW, "Reset visualizzazione"),
    ]

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)

    # Chi ha fatto l’azione (admin o dipendente loggato)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events"
    )

    # A chi si riferisce (dipendente/payslip)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")
    payslip = models.ForeignKey(Payslip, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events")

    # Contesto tecnico (utile come prova)
    ip_address = models.CharField(max_length=64, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    # Extra info (es: "import", "single upload", note)
    metadata = models.JSONField(blank=True, null=True, default=dict)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at} {self.action} {self.employee or '-'} {self.payslip or '-'}"