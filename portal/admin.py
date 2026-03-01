import uuid
from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'external_code', 'tasto_invito')
    fields = ('user', 'full_name', 'external_code', 'email_invio', 'tasto_invito_scheda')
    readonly_fields = ('tasto_invito_scheda',)

    def tasto_invito(self, obj):
        # Se il token manca o è vuoto, lo generiamo e salviamo
        if not getattr(obj, 'registration_token', None):
            obj.registration_token = str(uuid.uuid4())
            # Usiamo save_base per evitare conflitti con altri segnali
            obj.save(update_fields=['registration_token'])
        
        url = f"https://cedolini-web.onrender.com/register/{obj.registration_token}/"
        return format_html(
            '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Copiato!\')" '
            'style="background:#417690; color:white; border:none; padding:3px 8px; cursor:pointer; border-radius:3px; font-size:10px;">'
            'Copia Link</button>', url
        )

    def tasto_invito_scheda(self, obj):
        if not getattr(obj, 'registration_token', None):
            return "Salva per generare il token"
            
        url = f"https://cedolini-web.onrender.com/register/{obj.registration_token}/"
        return format_html(
            '<div style="padding:10px; border:1px solid #ccc; background:#eee; display:inline-block;">'
            '<code style="font-weight:bold; color:#c4183c;">{}</code>'
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