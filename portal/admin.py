from django.contrib import admin
from django.utils.html import format_html
from .models import Employee, Payslip, AuditEvent


admin.site.site_header = "Admin"
admin.site.site_title = "Admin"
admin.site.index_title = "Pannello di Amministrazione"


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'external_code', 'must_change_password', 'invito_inviato')
    search_fields = ('full_name', 'external_code')
    list_filter = ('must_change_password', 'invito_inviato')


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


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'actor_user', 'employee')
    list_filter = ('action',)
    search_fields = ('employee__full_name',)