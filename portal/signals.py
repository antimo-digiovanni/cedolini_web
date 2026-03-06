from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import User

from .models import Employee, AuditEvent, Payslip, Cud


@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    # Nessun invio automatico, usiamo il link manuale dall'admin
    pass


@receiver(user_logged_in, sender=User)
def log_user_login(sender, request, user, **kwargs):
    """Crea un AuditEvent ad ogni login riuscito."""
    try:
        employee = getattr(user, "employee", None)
        ip = request.META.get("REMOTE_ADDR") if request else None
        ua = request.META.get("HTTP_USER_AGENT", "") if request else ""

        AuditEvent.objects.create(
            action="user_logged_in",
            actor_user=user,
            employee=employee,
            ip_address=ip,
            user_agent=ua,
            metadata={},
        )
    except Exception:
        # Non bloccare mai il login per problemi di logging
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Errore nella creazione di AuditEvent per user_logged_in")


@receiver(post_delete, sender=Payslip)
def delete_payslip_file_on_model_delete(sender, instance, **kwargs):
    """Rimuove il PDF dal bucket quando il record Payslip viene eliminato."""
    try:
        if instance.pdf:
            instance.pdf.delete(save=False)
    except Exception:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Errore nella cancellazione file Payslip id=%s", getattr(instance, "id", None))


@receiver(post_delete, sender=Cud)
def delete_cud_file_on_model_delete(sender, instance, **kwargs):
    """Rimuove il PDF CUD dal bucket quando il record Cud viene eliminato."""
    try:
        if instance.pdf:
            instance.pdf.delete(save=False)
    except Exception:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Errore nella cancellazione file CUD id=%s", getattr(instance, "id", None))