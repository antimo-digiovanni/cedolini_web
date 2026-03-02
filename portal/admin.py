from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent


# =============================
# PERSONALIZZAZIONE TITOLO ADMIN
# =============================

admin.site.site_header = "Admin"
admin.site.site_title = "Admin"
admin.site.index_title = "Pannello di Amministrazione"


# =============================
# EMPLOYEE ADMIN
# =============================

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'external_code', 'copia_invito')
    search_fields = ('full_name', 'external_code')
    list_filter = ('must_change_password',)

    def copia_invito(self, obj):
        if obj.user:
            url = f"https://cedolini-web.onrender.com/register/{obj.user.username}/"
            return format_html(
                """
                <button type="button"
                    onclick="navigator.clipboard.writeText('{}'); alert('Link copiato!')"
                    style="
                        background:#2563eb;
                        color:white;
                        border:none;
                        padding:5px 12px;
                        cursor:pointer;
                        border-radius:6px;
                        font-size:12px;
                    ">
                    Copia Link
                </button>
                """,
                url
            )
        return "Nessun utente"


# =============================
# ALTRI MODELLI
# =============================

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'month', 'year', 'uploaded_at')
    list_filter = ('year', 'month')
    search_fields = ('employee__full_name',)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'actor_user', 'employee')
    list_filter = ('action',)
    search_fields = ('employee__full_name',)