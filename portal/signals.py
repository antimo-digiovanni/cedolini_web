from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    # Invia la mail solo se c'è un'email e l'invito non è ancora stato inviato
    if instance.email_invio and not instance.invito_inviato:
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
            # Segna come inviato per non mandarlo all'infinito ad ogni modifica
            Employee.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ Email di invito inviata a {instance.email_invio}")
        except Exception as e:
            print(f"❌ Errore durante l'invio dell'invito: {e}")