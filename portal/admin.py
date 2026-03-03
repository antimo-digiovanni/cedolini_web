from django.contrib import admin
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta

from .models import Employee, Payslip, AuditEvent, InviteToken


admin.site.site_header = "Admin"
admin.site.site_title = "Admin"
admin.site.index_title = "Pannello di Amministrazione"


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'external_code', 'must_change_password', 'invito_inviato')
    search_fields = ('first_name', 'last_name', 'external_code')
    list_filter = ('must_change_password', 'invito_inviato')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.email_invio and not obj.invito_inviato:

            # Genera token
            token = get_random_string(64)

            InviteToken.objects.create(
                employee=obj,
                token=token,
                expires_at=timezone.now() + timedelta(days=3)
            )

            link = f"https://cedolini-web.onrender.com/portal/register/{token}/"

            subject = "Accesso Portale Cedolini"

            text_content = f"""
Ciao {obj.first_name} {obj.last_name},

Sei stato invitato ad accedere al Portale Cedolini.

Completa la registrazione da qui:
{link}
"""

            html_content = f"""
<!DOCTYPE html>
<html>
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
            Benvenuto nel Portale Cedolini
        </td>
    </tr>

    <tr>
        <td style="font-size:14px;color:#374151;padding-bottom:20px;">
            Gentile <strong>{obj.first_name} {obj.last_name}</strong>,<br><br>
            tramite questo portale potrai:
            <ul>
                <li>Visualizzare i tuoi cedolini</li>
                <li>Scaricare i PDF</li>
                <li>Consultare lo storico</li>
            </ul>
        </td>
    </tr>

    <tr>
        <td align="center" style="padding:30px 0;">
            <a href="{link}" 
               style="background:#1f2937;color:#ffffff;padding:12px 24px;
               text-decoration:none;border-radius:6px;font-weight:bold;">
               Completa Registrazione
            </a>
        </td>
    </tr>

    <tr>
        <td style="font-size:12px;color:#6b7280;padding-top:20px;">
            Il link è valido per 3 giorni.
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
    list_display = ('employee', 'year', 'month', 'uploaded_at')
    list_filter = ('year', 'month')


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'actor_user', 'employee')
    list_filter = ('action',)