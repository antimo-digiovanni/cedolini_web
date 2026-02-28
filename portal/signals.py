from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee, Payslip
import logging

# Configurazione del logger per Render
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    """
    Invia l'email di benvenuto prendendo l'email dall'Utente collegato.
    """
    try:
        # Cerchiamo l'email nell'utente (User) collegato al dipendente
        user_obj = instance.user
        email_destinatario = user_obj.email if user_obj else None

        # Se non c'è nell'utente, proviamo a vedere se esiste un campo email_invio sul modello
        if not email_destinatario and hasattr(instance, 'email_invio'):
            email_destinatario = instance.email_invio

        # Procediamo solo se abbiamo una mail e non è già stata inviata
        if email_destinatario and not instance.invito_inviato:
            print(f"--- Tentativo invio invito a: {email_destinatario} ---")
            
            subject = "Benvenuto nel Portale Cedolini - San Vincenzo"
            message = (
                f"Ciao {instance.full_name},\n\n"
                f"Il tuo profilo è stato creato con successo. Puoi completare la registrazione "
                f"cliccando qui: {settings.DEFAULT_PROTOCOL}://{settings.DEFAULT_DOMAIN}/register/\n\n"
                "Servizio San Vincenzo SRL"
            )
            
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email_destinatario],
                fail_silently=False
            )
            
            # Usiamo .update() per evitare che questa riga faccia ripartire il segnale (loop)
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ Email inviata con successo a {email_destinatario}")

    except Exception as e:
        # Questo blocco impedisce al sito di andare in crash (Error 500)
        logger.error(f"❌ Errore critico nel segnale Employee: {e}")
        print(f"❌ ERRORE SEGNALE: {e}")


@receiver(post_save, sender=Payslip)
def notifica_nuovo_cedolino(sender, instance, created, **kwargs):
    """
    Invia una notifica quando carichi un nuovo file PDF.
    """
    if created:
        try:
            # Recuperiamo l'email tramite la relazione Employee -> User
            email = instance.employee.user.email if instance.employee.user else None
            
            if email:
                send_mail(
                    f"Nuovo Cedolino Disponibile - {instance.month:02d}/{instance.year}",
                    f"Ciao {instance.employee.full_name}, un nuovo cedolino è disponibile nel portale.",
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False
                )
                print(f"✅ Notifica cedolino inviata a {email}")
        except Exception as e:
            logger.error(f"❌ Errore notifica cedolino: {e}")