from django.contrib import admin
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta

from .models import Employee, Payslip, Cud, AuditEvent, InviteToken


admin.site.site_header = "Amministrazione Portale Cedolini"
admin.site.site_title = "Portale Cedolini Admin"
admin.site.index_title = "Pannello di amministrazione"


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'external_code', 'must_change_password', 'invito_inviato')
    search_fields = ('first_name', 'last_name', 'external_code')
    list_filter = ('must_change_password', 'invito_inviato')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.email_invio and not obj.invito_inviato:

            token = get_random_string(64)

            InviteToken.objects.create(
                employee=obj,
                token=token,
                expires_at=timezone.now() + timedelta(days=7)
            )

            link = f"https://cedolini-web.onrender.com/portal/register/{token}/"
            username = obj.user.username

            subject = "Attivazione account - Portale Cedolini"

            text_content = f"""
Gentile {obj.first_name} {obj.last_name},

è stato creato il tuo accesso al Portale Cedolini.

USERNAME: {username}

Ti servirà questo username per effettuare il login al portale.

Clicca sul link seguente per attivare il tuo account e creare la password:
{link}

Il link è valido per 7 giorni.

Cordiali saluti
San Vincenzo Srl
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
        <td style="font-size:22px;font-weight:bold;color:#1f2937;padding-bottom:20px;">
            Attivazione Portale Cedolini
        </td>
    </tr>

    <tr>
        <td style="font-size:14px;color:#374151;padding-bottom:20px;">
            Gentile <strong>{obj.first_name} {obj.last_name}</strong>,<br><br>
            è stato creato il tuo accesso al Portale Cedolini.
        </td>
    </tr>

    <tr>
        <td style="padding:20px;background:#f3f4f6;border-radius:8px;text-align:center;">
            <div style="font-size:13px;color:#6b7280;">Username per il login</div>
            <div style="font-size:20px;font-weight:bold;color:#1e3a8a;margin-top:5px;">
                {username}
            </div>
            <div style="font-size:12px;color:#6b7280;margin-top:5px;">
                Conserva questo username: ti servirà per accedere al portale.
            </div>
        </td>
    </tr>

    <tr>
        <td align="center" style="padding:30px 0;">
            <a href="{link}" 
               style="background:#2563eb;color:#ffffff;padding:14px 28px;
               text-decoration:none;border-radius:6px;font-weight:bold;">
               Attiva il tuo account
            </a>
        </td>
    </tr>

    <tr>
        <td style="font-size:12px;color:#6b7280;">
            Il link è valido per 7 giorni.
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


@admin.register(Cud)
class CudAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'uploaded_at')
    list_filter = ('year',)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'actor_user', 'employee')
    list_filter = ('action',)