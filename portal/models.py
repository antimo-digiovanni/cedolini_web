from django.db import models
from django.contrib.auth.models import User


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    full_name = models.CharField(max_length=160)
    email_invio = models.EmailField(max_length=255, blank=True, null=True)
    invito_inviato = models.BooleanField(default=False)
    external_code = models.CharField(max_length=10, blank=True, null=True)
    must_change_password = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name


class Payslip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payslips")
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    pdf = models.FileField(upload_to="payslips/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("employee", "year", "month")]


class PayslipView(models.Model):
    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)


class AuditEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)
    actor_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    payslip = models.ForeignKey(Payslip, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True, default=dict)


# 🔥 MODELLO PER BARRA DI AVANZAMENTO IMPORT
class ImportJob(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    total_files = models.IntegerField(default=0)
    processed_files = models.IntegerField(default=0)
    created_users = models.IntegerField(default=0)
    created_payslips = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="processing")  # processing | completed | error
    error_message = models.TextField(blank=True, null=True)