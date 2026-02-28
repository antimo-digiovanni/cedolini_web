from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Visualizziamo il nome, il codice e il nuovo campo per il link
    list_display = ('full_name', 'external_code', 'invito_inviato', 'copia_link_invito')
    fields = ('user', 'full_name', 'external_code', 'email_invio', 'invito_inviato')
    readonly_fields = ('invito_inviato',)

    def copia_link_invito(self, obj):
        if not obj.registration_token:
            return "Token mancante"
        
        # Genera il link reale per la registrazione
        url = f"https://cedolini-web.onrender.com/register/{obj.registration_token}/"
        
        # HTML per il box con tasto "Copia"
        return format_html(
            '<div style="display:flex; align-items:center;">'
            '<input type="text" value="{}" id="link_{}" readonly '
            'style="width:120px; font-size:10px; padding:2px; border:1px solid #ccc; margin-right:5px;">'
            '<button type="button" onclick="const el=document.getElementById(\'link_{}\'); el.select(); document.execCommand(\'copy\'); alert(\'Link copiato!\');" '
            'style="background:#417690; color:white; border:none; padding:3px 8px; cursor:pointer; border-radius:3px; font-size:10px;">'
            'Copia</button>'
            '</div>',
            url, obj.pk, obj.pk
        )

    copia_link_invito.short_description = "Link Registrazione"

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'month')

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action')