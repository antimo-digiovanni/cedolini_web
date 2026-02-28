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
    Invia l'email di benvenuto/registrazione usando l'email dell'Utente collegato.
    """
    # Recuperiamo l'email dall'oggetto User collegato all'Employee
    email_destinatario = instance.user.email
    
    # Parte solo se l'email è presente e non è stata già inviata la notifica
    if email_destinatario and not instance.invito_inviato:
        print(f"--- Tentativo invio invito a: {email_destinatario} ---")
        
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
                [email_destinatario], 
                fail_silently=False
            )
            
            # Segna l'invio come effettuato nel database
            Employee.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ Successo: Email di invito inviata a {email_destinatario}")
            
        except Exception as e:
            print(f"❌ ERRORE INVIO EMAIL INVITO: {type(e).__name__} - {str(e)}")
            logger.error(f"Errore critico email invito: {e}")


@receiver(post_save, sender=Payslip)
def notifica_nuovo_cedolino(sender, instance, created, **kwargs):
    """
    Invia una notifica automatica quando viene caricato un nuovo PDF.
    """
    if created:
        # Recuperiamo l'email dall'Utente collegato al dipendente
        email_destinatario = instance.employee.user.email
        
        if email_destinatario:
            print(f"--- Tentativo invio notifica cedolino a: {email_destinatario} ---")
            
            subject = f"Nuovo Cedolino Disponibile - {instance.month:02d}/{instance.year}"
            message = (
                f"Ciao {instance.employee.full_name},\n\n"
                f"Ti informiamo che è stato caricato il tuo cedolino relativo a {instance.month:02d}/{instance.year}.\n\n"
                f"Puoi visualizzarlo accedendo qui: "
                f"{settings.DEFAULT_PROTOCOL}://{settings.DEFAULT_DOMAIN}/login/\n\n"
                "Servizio San Vincenzo SRL"
            )
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [email_destinatario],
                    fail_silently=False
                )
                print(f"✅ Successo: Notifica cedolino inviata a {email_destinatario}")
            except Exception as e:
                print(f"❌ ERRORE INVIO NOTIFICA CEDOLINO: {type(e).__name__} - {str(e)}")
                logger.error(f"Errore critico notifica cedolino: {e}")