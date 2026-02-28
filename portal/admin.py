from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Usiamo solo campi che sicuramente esistono (Nome e Codice Esterno)
    list_display = ('full_name', 'external_code', 'tasto_registrazione')
    
    def tasto_registrazione(self, obj):
        # Cerchiamo il token provando diversi nomi comuni
        token = getattr(obj, 'registration_token', 
                getattr(obj, 'token', 
                getattr(obj, 'registration_code', None)))
        
        if not token:
            return "Token non trovato"
            
        url = f"https://cedolini-web.onrender.com/register/{token}/"
        
        return format_html(
            '<a href="javascript:void(0)" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Copiato!\')" '
            'style="background:#264b5d; color:white; padding:5px 10px; text-decoration:none; border-radius:4px; font-weight:bold; font-size:11px;">'
            'COPIA LINK</a>',
            url
        )

    tasto_registrazione.short_description = "Link Invito"

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Payslip._meta.fields if field.name != 'id']

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = [field.name for field in AuditEvent._meta.fields if field.name != 'id']