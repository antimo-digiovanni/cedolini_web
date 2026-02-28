from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    # Usiamo un blocco try/except che avvolge TUTTO
    try:
        # Recupero email
        email = getattr(instance, 'email_invio', None)
        
        # Se c'è l'email e non è stato ancora inviato
        if email and not instance.invito_inviato:
            print(f"Tentativo invio a: {email}")
            
            send_mail(
                "Benvenuto nel Portale Cedolini",
                f"Ciao {instance.full_name}, il tuo profilo è pronto.",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=True  # Impedisce al sito di andare in errore 500
            )
            
            # Aggiorna il database senza scatenare altri segnali
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
            
    except Exception as e:
        # Se c'è un errore, lo scrive nei log ma NON blocca il salvataggio
        print(f"Errore nel segnale: {e}")