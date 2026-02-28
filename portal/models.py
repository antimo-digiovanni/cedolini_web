from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    full_name = models.CharField(max_length=160)
    
    # QUESTI SONO I CAMPI CHE MANCANO NELLA TUA SCHERMATA
    email_invio = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email per invio credenziali")
    invito_inviato = models.BooleanField(default=False, verbose_name="Invito già inviato")
    
    external_code = models.CharField(max_length=10, blank=True, null=True)
    must_change_password = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.full_name} ({self.external_code})" if self.external_code else self.full_name

class Payslip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payslips")
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    pdf = models.FileField(upload_to="payslips/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("employee", "year", "month")]

    def __str__(self):
        return f"Cedolino {self.month}/{self.year} - {self.employee.full_name}"

class PayslipView(models.Model):
    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE, related_name="views")
    viewed_at = models.DateTimeField(auto_now_add=True)

class AuditEvent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)
    actor_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    payslip = models.ForeignKey(Payslip, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)