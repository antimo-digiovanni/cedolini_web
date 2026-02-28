from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee, Payslip
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    """Invia email di benvenuto senza mai bloccare il sito."""
    try:
        # 1. Cerchiamo l'email (prima sull'utente, poi sul profilo se esiste)
        email_destinatario = None
        if instance.user and instance.user.email:
            email_destinatario = instance.user.email
        elif hasattr(instance, 'email_invio') and instance.email_invio:
            email_destinatario = instance.email_invio

        # 2. Procediamo solo se abbiamo una mail e non abbiamo ancora inviato l'invito
        if email_destinatario and not instance.invito_inviato:
            print(f"--- Tentativo invio invito a: {email_destinatario} ---")
            
            send_mail(
                "Benvenuto nel Portale Cedolini - San Vincenzo",
                f"Ciao {instance.full_name},\n\nIl tuo profilo è pronto. Registrati qui: {settings.DEFAULT_PROTOCOL}://{settings.DEFAULT_DOMAIN}/register/",
                settings.EMAIL_HOST_USER,
                [email_destinatario],
                fail_silently=False
            )
            
            # Segnamo come inviato usando update per evitare loop di segnali
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ Email inviata con successo a {email_destinatario}")
            
    except Exception as e:
        # Fondamentale: l'errore viene scritto nei log ma il sito NON si blocca
        logger.error(f"❌ Errore invio mail: {e}")
        print(f"❌ ERRORE: {e}")

@receiver(post_save, sender=Payslip)
def notifica_nuovo_cedolino(sender, instance, created, **kwargs):
    """Notifica automatica per caricamento PDF."""
    if created:
        try:
            email = None
            if instance.employee.user and instance.employee.user.email:
                email = instance.employee.user.email
            
            if email:
                send_mail(
                    f"Nuovo Cedolino Disponibile - {instance.month:02d}/{instance.year}",
                    f"Ciao {instance.employee.full_name}, un nuovo cedolino è disponibile.",
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False
                )
        except Exception as e:
            logger.error(f"❌ Errore notifica cedolino: {e}")