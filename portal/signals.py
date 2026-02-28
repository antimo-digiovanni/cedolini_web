from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee
import threading

def send_email_async(subject, message, recipient_list):
    try:
        print(f"DEBUG: Avvio invio mail a {recipient_list}...")
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            recipient_list,
            fail_silently=False # Qui vogliamo vedere l'errore!
        )
        print(f"DEBUG: ✅ Mail inviata con successo a {recipient_list}")
    except Exception as e:
        print(f"DEBUG: ❌ ERRORE GMAIL: {e}")

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, **kwargs):
    try:
        email = instance.email_invio
        if email and not instance.invito_inviato:
            thread = threading.Thread(
                target=send_email_async,
                args=(
                    "Benvenuto nel Portale Cedolini",
                    f"Ciao {instance.full_name}, il tuo profilo è pronto.",
                    [email]
                )
            )
            thread.start()
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"DEBUG: Thread lanciato per {email}")
    except Exception as e:
        print(f"DEBUG: Errore segnale: {e}")