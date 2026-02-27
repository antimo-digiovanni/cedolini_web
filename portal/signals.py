from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee
import logging

# Configurazione log per vedere gli errori su Render
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    # Parte solo se l'email è presente e non è stata già inviata la notifica
    if instance.email_invio and not instance.invito_inviato:
        print(f"--- Tentativo invio invito a: {instance.email_invio} ---")
        
        subject = "Benvenuto nel Portale Cedolini - San Vincenzo"
        message = (
            f"Ciao {instance.full_name},\n\n"
            f"Il tuo profilo è stato creato. Puoi registrarti al portale per scaricare i tuoi cedolini "
            f"cliccando qui: {settings.DEFAULT_PROTOCOL}://{settings.DEFAULT_DOMAIN}/register/\n\n"
            "Servizio San Vincenzo SRL"
        )
        
        try:
            send_mail(
                subject, 
                message, 
                settings.EMAIL_HOST_USER, 
                [instance.email_invio], 
                fail_silently=False
            )
            
            # Aggiorna il database per non inviare di nuovo
            Employee.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ Successo: Email di invito inviata a {instance.email_invio}")
            
        except Exception as e:
            # Questo stamperà l'errore specifico (es. errore autenticazione Aruba)
            print(f"❌ ERRORE INVIO EMAIL: {type(e).__name__} - {str(e)}")
            logger.error(f"Errore critico email: {e}")