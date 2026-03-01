from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'external_code', 'copia_invito')
    fields = ('user', 'full_name', 'external_code', 'email_invio', 'box_link')
    readonly_fields = ('box_link',)
    
    def copia_invito(self, obj):
        if obj.user:
            url = f"https://cedolini-web.onrender.com/register/{obj.user.username}/"
            return format_html('<button type="button" onclick="navigator.clipboard.writeText(\'{}\'); alert(\'Copiato!\')" style="background:#417690; color:white; border:none; padding:3px 8px; cursor:pointer; border-radius:3px;">Copia</button>', url)
        return "No User"

    def box_link(self, obj):
        if obj.user:
            url = f"https://cedolini-web.onrender.com/register/{obj.user.username}/"
            return format_html('<div style="padding:10px; background:#eee; border:1px solid #ccc;"><code>{}</code></div>', url)
        return "Nessun utente collegato"

admin.site.register(Payslip)
admin.site.register(AuditEvent)