from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Visualizziamo solo quello che esiste nel tuo models.py
    list_display = ('full_name', 'external_code', 'email_invio', 'invito_inviato', 'tasto_invito_manuale')
    fields = ('user', 'full_name', 'external_code', 'email_invio', 'invito_inviato', 'must_change_password', 'link_invito_scheda')
    readonly_fields = ('link_invito_scheda',)

    def tasto_invito_manuale(self, obj):
        # Usiamo lo username come "token" visto che il campo token non esiste
        if obj.user:
            username = obj.user.username
            url = f"https://cedolini-web.onrender.com/register/{username}/"
            return format_html(
                '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Link Copiato!\')" '
                'style="background:#417690; color:white; border:none; padding:3px 8px; cursor:pointer; border-radius:3px; font-size:10px;">'
                'Copia Link</button>', url
            )
        return "Utente non collegato"

    def link_invito_scheda(self, obj):
        if obj.user:
            username = obj.user.username
            url = f"https://cedolini-web.onrender.com/register/{username}/"
            return format_html(
                '<div style="padding:10px; background:#f0f0f0; border:1px solid #ccc; display:inline-block;">'
                '<code style="font-weight:bold; color:#c4183c; margin-right:15px;">{}</code>'
                '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Link Copiato!\')" '
                'style="background:#264b5d; color:white; border:none; padding:5px 15px; cursor:pointer; border-radius:4px;">'
                'COPIA LINK</button></div>', url, url
            )
        return "Associa un utente per vedere il link"

    tasto_invito_manuale.short_description = "Invito"
    link_invito_scheda.short_description = "Link Registrazione"

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'month')

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'employee')