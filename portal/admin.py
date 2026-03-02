from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
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
    list_display = ('full_name', 'external_code', 'must_change_password', 'copia_invito')
    search_fields = ('full_name', 'external_code')
    list_filter = ('must_change_password',)

    def copia_invito(self, obj):
        if obj.user:
            # genera URL dinamicamente corretto
            relative_url = reverse('register_view', args=[obj.user.username])
            full_url = f"https://cedolini-web.onrender.com{relative_url}"

            return format_html(
                """
                <button type="button"
                    onclick="navigator.clipboard.writeText('{}'); alert('Link copiato!')"
                    style="
                        background:#2563eb;
                        color:white;
                        border:none;
                        padding:6px 12px;
                        cursor:pointer;
                        border-radius:8px;
                        font-size:12px;
                        font-weight:600;
                    ">
                    Copia Link
                </button>
                """,
                full_url
            )
        return "Nessun utente"


# =============================
# PAYSLIP ADMIN
# =============================

@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('employee', 'mese_legibile', 'year', 'uploaded_at')
    list_filter = ('year', 'month')
    search_fields = ('employee__full_name',)

    def mese_legibile(self, obj):
        mesi = [
            "", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
        ]
        return mesi[obj.month]

    mese_legibile.short_description = "Mese"


# =============================
# AUDIT ADMIN
# =============================

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'actor_user', 'employee')
    list_filter = ('action',)
    search_fields = ('employee__full_name',)