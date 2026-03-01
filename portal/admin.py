from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'external_code', 'email_invio', 'tasto_invito_veloce')
    fields = ('user', 'full_name', 'external_code', 'email_invio', 'invito_inviato', 'box_link_registrazione')
    readonly_fields = ('box_link_registrazione',)

    def tasto_invito_veloce(self, obj):
        if obj.user:
            url = f"https://cedolini-web.onrender.com/register/{obj.user.username}/"
            return format_html(
                '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Copiato!\')" '
                'style="background:#417690; color:white; border:none; padding:3px 8px; cursor:pointer; border-radius:3px; font-size:10px;">'
                'Copia</button>', url
            )
        return "No User"

    def box_link_registrazione(self, obj):
        if obj.user:
            url = f"https://cedolini-web.onrender.com/register/{obj.user.username}/"
            return format_html(
                '<div style="padding:10px; background:#f8f8f8; border:1px solid #ddd; border-radius:4px;">'
                '<code style="font-weight:bold; color:#c4183c; margin-right:15px;">{}</code>'
                '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Copiato!\')" '
                'style="background:#264b5d; color:white; border:none; padding:5px 15px; cursor:pointer; border-radius:4px;">'
                'COPIA LINK</button></div>', url, url
            )
        return "Associa un utente per vedere il link"

    tasto_invito_veloce.short_description = "Copia"
    box_link_registrazione.short_description = "Link Invito"

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'month')

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'employee')