from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import User

from .models import Employee, AuditEvent


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