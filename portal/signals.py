from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee, Payslip
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    """Invia email di benvenuto cercando l'email nel profilo o nell'utente."""
    try:
        # 1. Cerchiamo l'email (prima nel campo email_invio, poi nell'utente Django)
        email_destinatario = instance.email_invio or (instance.user.email if instance.user else None)

        if not email_destinatario:
            print(f"⚠️ Nessuna email trovata per {instance.full_name}. Inseriscila nell'Admin.")
            return

        # 2. Procediamo solo se non abbiamo ancora inviato l'invito
        if not instance.invito_inviato:
            print(f"📧 --- Tentativo invio invito a: {email_destinatario} ---")
            
            subject = "Benvenuto nel Portale Cedolini - San Vincenzo"
            message = (
                f"Ciao {instance.full_name},\n\nil tuo profilo è stato creato. "
                f"Registrati qui: {settings.DEFAULT_PROTOCOL}://{settings.DEFAULT_DOMAIN}/register/\n\n"
                "Servizio San Vincenzo SRL"
            )
            
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email_destinatario],
                fail_silently=False
            )
            
            # Aggiorniamo il database marcando come inviato
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ Email inviata con successo a {email_destinatario}")
        else:
            print(f"ℹ️ Invito già inviato in precedenza a {email_destinatario}")

    except Exception as e:
        logger.error(f"❌ Errore critico invio mail: {e}")
        print(f"❌ ERRORE: {e}")

@receiver(post_save, sender=Payslip)
def notifica_nuovo_cedolino(sender, instance, created, **kwargs):
    """Notifica automatica per nuovo cedolino."""
    if created:
        try:
            employee = instance.employee
            email_dest = employee.email_invio or (employee.user.email if employee.user else None)
            
            if email_dest:
                send_mail(
                    f"Nuovo Cedolino Disponibile - {instance.month:02d}/{instance.year}",
                    f"Ciao {employee.full_name}, un nuovo cedolino è stato caricato.",
                    settings.EMAIL_HOST_USER,
                    [email_dest],
                    fail_silently=False
                )
                print(f"✅ Notifica cedolino inviata a {email_dest}")
        except Exception as e:
            logger.error(f"❌ Errore notifica cedolino: {e}")