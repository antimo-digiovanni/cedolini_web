from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee, Payslip
import logging

# Configurazione log per vedere gli errori su Render
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    """
    Invia l'email di benvenuto prendendo l'indirizzo dall'Utente Django.
    """
    try:
        # Verifichiamo se l'utente collegato ha una mail inserita
        if instance.user and instance.user.email:
            email_destinatario = instance.user.email
            
            # Invia solo se non è già stato inviato in precedenza
            if not instance.invito_inviato:
                print(f"--- Tentativo invio invito a: {email_destinatario} ---")
                
                subject = "Benvenuto nel Portale Cedolini - San Vincenzo"
                message = (
                    f"Ciao {instance.full_name},\n\n"
                    f"Il tuo profilo è stato creato. Puoi registrarti qui per scaricare i cedolini: "
                    f"{settings.DEFAULT_PROTOCOL}://{settings.DEFAULT_DOMAIN}/register/\n\n"
                    "Servizio San Vincenzo SRL"
                )
                
                send_mail(
                    subject, 
                    message, 
                    settings.EMAIL_HOST_USER, 
                    [email_destinatario], 
                    fail_silently=False
                )
                
                # Segna l'invio come fatto per evitare duplicati
                Employee.objects.filter(pk=instance.pk).update(invito_inviato=True)
                print(f"✅ Successo: Email inviata a {email_destinatario}")
        else:
            print("⚠️ Attenzione: L'utente collegato non ha un indirizzo email.")

    except Exception as e:
        # Evita il crash del sito e scrive l'errore nei log
        logger.error(f"❌ Errore critico invio email: {e}")
        print(f"❌ ERRORE: {e}")


@receiver(post_save, sender=Payslip)
def notifica_nuovo_cedolino(sender, instance, created, **kwargs):
    """
    Notifica automatica quando carichi un PDF.
    """
    if created:
        try:
            if instance.employee.user and instance.employee.user.email:
                user_email = instance.employee.user.email
                
                send_mail(
                    f"Nuovo Cedolino Disponibile - {instance.month:02d}/{instance.year}",
                    f"Ciao {instance.employee.full_name}, un nuovo cedolino è stato caricato sul portale.",
                    settings.EMAIL_HOST_USER,
                    [user_email],
                    fail_silently=False
                )
                print(f"✅ Notifica cedolino inviata a {user_email}")
        except Exception as e:
            logger.error(f"❌ Errore notifica cedolino: {e}")