from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'external_code', 'copia_invito')
    
    def copia_invito(self, obj):
        if obj.user:
            url = f"https://cedolini-web.onrender.com/register/{obj.user.username}/"
            return format_html(
                '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Link Copiato!\')" '
                'style="background:#417690; color:white; border:none; padding:3px 8px; cursor:pointer; border-radius:3px; font-size:10px;">'
                'Copia Link</button>', url
            )
        return "Nessun Utente"

admin.site.register(Payslip)
admin.site.register(AuditEvent)