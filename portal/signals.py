from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    """
    Riattiviamo l'invio. Se fallisce, il sito continuerà a funzionare
    grazie a fail_silently=True.
    """
    try:
        # Usiamo il campo email_invio che abbiamo visto funzionare nell'Admin
        email_dest = instance.email_invio
        
        if email_dest and not instance.invito_inviato:
            print(f"📧 Tentativo invio invito a: {email_dest}")
            
            send_mail(
                "Benvenuto nel Portale Cedolini",
                f"Ciao {instance.full_name}, il tuo profilo è pronto. Registrati qui: {settings.DEFAULT_PROTOCOL}://{settings.DEFAULT_DOMAIN}/register/",
                settings.EMAIL_HOST_USER,
                [email_dest],
                fail_silently=True  # <--- Fondamentale per evitare il crash
            )
            
            # Segniamo come inviato
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ Operazione conclusa per {email_dest}")
            
    except Exception as e:
        print(f"⚠️ Errore durante l'esecuzione del segnale: {e}")