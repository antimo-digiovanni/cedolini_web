from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee
import threading

def send_email_async(subject, message, recipient_list):
    """Funzione per inviare la mail in background"""
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        recipient_list,
        fail_silently=False
    )

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, **kwargs):
    try:
        email = instance.email_invio
        if email and not instance.invito_inviato:
            # Avvia l'invio in un thread separato (il server non aspetta più!)
            thread = threading.Thread(
                target=send_email_async,
                args=(
                    "Benvenuto nel Portale Cedolini",
                    f"Ciao {instance.full_name}, il tuo profilo è pronto.",
                    [email]
                )
            )
            thread.start()
            
            # Segna come inviato nel database
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
    except:
        pass