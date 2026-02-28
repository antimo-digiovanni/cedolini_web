import uuid
from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Campi nella lista generale
    list_display = ('full_name', 'external_code', 'invito_inviato', 'tasto_copia_rapido')
    
    # Campi nella scheda singola
    fields = ('user', 'full_name', 'external_code', 'email_invio', 'invito_inviato', 'mostra_link_registrazione')
    readonly_fields = ('mostra_link_registrazione',)

    def tasto_copia_rapido(self, obj):
        # Se il token manca, lo generiamo e salviamo subito
        if not getattr(obj, 'registration_token', None):
            obj.registration_token = str(uuid.uuid4())
            obj.save(update_fields=['registration_token'])
        
        url = f"https://cedolini-web.onrender.com/register/{obj.registration_token}/"
        
        return format_html(
            '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Copiato!\')" '
            'style="background:#417690; color:white; border:none; padding:3px 8px; cursor:pointer; border-radius:3px; font-size:10px;">'
            'Copia</button>', url
        )

    def mostra_link_registrazione(self, obj):
        # Se il token manca, lo generiamo e salviamo subito
        if not getattr(obj, 'registration_token', None):
            obj.registration_token = str(uuid.uuid4())
            obj.save(update_fields=['registration_token'])
            
        url = f"https://cedolini-web.onrender.com/register/{obj.registration_token}/"
        
        return format_html(
            '<div style="background: #f8f8f8; padding: 10px; border: 1px solid #ddd; border-radius: 4px; display: inline-block;">'
            '<code style="font-weight: bold; color: #c4183c; margin-right: 15px;">{}</code>'
            '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Link copiato!\')" '
            'style="background: #264b5d; color: white; border: none; padding: 5px 15px; cursor: pointer; border-radius: 4px;">'
            'COPIA LINK</button>'
            '</div>', url, url
        )

    tasto_copia_rapido.short_description = "Copia"
    mostra_link_registrazione.short_description = "Link di Registrazione"

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Payslip._meta.fields if field.name != 'id']

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = [field.name for field in AuditEvent._meta.fields if field.name != 'id']