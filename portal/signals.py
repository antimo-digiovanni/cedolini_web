from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee
import threading

def send_email_async(subject, message, recipient_list):
    try:
        print(f"DEBUG: Tentativo invio mail a {recipient_list}")
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            recipient_list,
            fail_silently=False
        )
        print(f"DEBUG: ✅ Mail inviata con successo!")
    except Exception as e:
        print(f"DEBUG: ❌ ERRORE GMAIL: {str(e)}")

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    try:
        # Usiamo il campo email_invio
        email = instance.email_invio
        if email and not instance.invito_inviato:
            # Creiamo il messaggio
            subject = "Benvenuto nel Portale Cedolini"
            message = f"Ciao {instance.full_name}, il tuo profilo è pronto."
            
            # Lanciamo il thread
            t = threading.Thread(
                target=send_email_async,
                args=(subject, message, [email])
            )
            t.start()
            
            # Segniamo come inviato nel DB
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"DEBUG: Thread lanciato per {email}")
    except Exception as e:
        print(f"DEBUG: Errore nel segnale: {str(e)}")