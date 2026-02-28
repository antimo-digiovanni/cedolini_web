from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Usiamo campi base che esistono al 100%
    list_display = ('full_name', 'external_code', 'tasto_invito')
    fields = ('user', 'full_name', 'external_code', 'email_invio', 'tasto_invito_scheda')
    readonly_fields = ('tasto_invito_scheda',)

    def tasto_invito(self, obj):
        # Proviamo a prendere il token, se non esiste usiamo l'ID (fallback)
        token = getattr(obj, 'registration_token', getattr(obj, 'token', obj.pk))
        url = f"https://cedolini-web.onrender.com/register/{token}/"
        
        return format_html(
            '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Copiato!\')" '
            'style="background:#417690; color:white; border:none; padding:3px 8px; cursor:pointer; border-radius:3px; font-size:10px;">'
            'Copia Link</button>', url
        )

    def tasto_invito_scheda(self, obj):
        token = getattr(obj, 'registration_token', getattr(obj, 'token', obj.pk))
        url = f"https://cedolini-web.onrender.com/register/{token}/"
        
        return format_html(
            '<div style="padding:10px; border:1px solid #ccc; background:#eee; display:inline-block;">'
            '<code style="font-weight:bold;">{}</code>'
            '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Copiato!\')" '
            'style="margin-left:15px; background:#264b5d; color:white; border:none; padding:5px 15px; cursor:pointer; border-radius:4px;">'
            'COPIA LINK</button></div>', url, url
        )

    tasto_invito.short_description = "Invito"
    tasto_invito_scheda.short_description = "Link Registrazione"

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'month')

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action')