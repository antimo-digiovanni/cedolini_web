from django.contrib import admin
from django.conf import settings
from django.core.mail import EmailMessage
from .models import Employee, Payslip, AuditEvent


admin.site.site_header = "Admin"
admin.site.site_title = "Admin"
admin.site.index_title = "Pannello di Amministrazione"


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'external_code', 'must_change_password', 'invito_inviato')
    search_fields = ('full_name', 'external_code')
    list_filter = ('must_change_password', 'invito_inviato')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.email_invio and not obj.invito_inviato:

            link = "https://cedolini-web.onrender.com/"

            email = EmailMessage(
                subject="Accesso Portale Cedolini",
                body=f"""
Ciao {obj.full_name},

Sei stato invitato ad accedere al portale cedolini.

Accedi da qui:
{link}

Username: {obj.user.username}

Al primo accesso ti verrà richiesto di cambiare password.
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[obj.email_invio],
                cc=["cedolini@sanvincenzosrl.com"],
            )

            email.send(fail_silently=False)

            obj.invito_inviato = True
            obj.save()


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