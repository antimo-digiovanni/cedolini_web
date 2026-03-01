from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'external_code', 'email_invio', 'tasto_copia_link')
    search_fields = ('full_name', 'external_code')
    
    def tasto_copia_link(self, obj):
        if obj.user:
            url = f"https://cedolini-web.onrender.com/register/{obj.user.username}/"
            return format_html(
                '<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Link copiato!\')" '
                'style="background:#417690; color:white; border:none; padding:4px 10px; cursor:pointer; border-radius:3px; font-weight:bold;">'
                'Copia Link</button>', url
            )
        return "Nessun Utente"
    
    tasto_copia_link.short_description = "Azione"

admin.site.register(Payslip)
admin.site.register(AuditEvent)