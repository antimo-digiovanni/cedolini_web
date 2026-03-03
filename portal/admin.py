from django.contrib import admin
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
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

            subject = "Accesso Portale Cedolini"

            text_content = f"""
Ciao {obj.full_name},

Sei stato invitato ad accedere al Portale Cedolini.

Accedi da qui:
{link}

Username: {obj.user.username}
"""

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
</head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:Arial, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
<tr>
<td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;padding:40px;">
    
    <tr>
        <td align="center" style="padding-bottom:20px;">
            <img src="https://cedolini-web.onrender.com/static/portal/logo.png" width="120">
        </td>
    </tr>

    <tr>
        <td style="font-size:20px;font-weight:bold;color:#1f2937;padding-bottom:20px;">
            Accesso Portale Cedolini
        </td>
    </tr>

    <tr>
        <td style="font-size:14px;color:#374151;padding-bottom:20px;">
            Gentile <strong>{obj.full_name}</strong>,<br><br>
            è stato creato il tuo accesso al portale aziendale.
        </td>
    </tr>

    <tr>
        <td style="font-size:14px;color:#374151;padding-bottom:10px;">
            <strong>Username:</strong> {obj.user.username}
        </td>
    </tr>

    <tr>
        <td align="center" style="padding:30px 0;">
            <a href="{link}" 
               style="background:#1f2937;color:#ffffff;padding:12px 24px;
               text-decoration:none;border-radius:6px;font-weight:bold;">
               Accedi al Portale
            </a>
        </td>
    </tr>

    <tr>
        <td style="font-size:12px;color:#6b7280;padding-top:20px;">
            Se non hai richiesto questo accesso puoi ignorare questa email.
        </td>
    </tr>

    <tr>
        <td style="font-size:12px;color:#9ca3af;padding-top:20px;">
            © San Vincenzo Srl
        </td>
    </tr>

</table>
</td>
</tr>
</table>
</body>
</html>
"""

            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [obj.email_invio],
                cc=["cedolini@sanvincenzosrl.com"],
            )

            email.attach_alternative(html_content, "text/html")
            email.send()

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