from django.contrib import admin
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Aggiungiamo i campi alla lista e al modulo di modifica
    list_display = ('full_name', 'external_code', 'email_invio', 'invito_inviato')
    fields = ('user', 'full_name', 'external_code', 'email_invio', 'invito_inviato', 'must_change_password')
    search_fields = ('full_name', 'external_code')

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'month', 'uploaded_at')

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'actor_user', 'employee', 'ip_address')