from django.contrib import admin
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Usiamo solo i campi base per essere sicuri che carichi
    list_display = ('full_name', 'external_code')
    fields = ('user', 'full_name', 'external_code', 'email_invio', 'invito_inviato')

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'month')

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action')