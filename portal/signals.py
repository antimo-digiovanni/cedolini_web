from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee, Payslip

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    """Tenta l'invio ma fail_silently=True impedisce il crash del sito"""
    try:
        # Prende l'email dal campo che abbiamo appena creato
        email_dest = instance.email_invio
        
        if email_dest and not instance.invito_inviato:
            print(f"📧 Tentativo invio a: {email_dest}")
            
            send_mail(
                "Benvenuto nel Portale Cedolini",
                f"Ciao {instance.full_name}, il tuo profilo è pronto. Registrati qui: {settings.DEFAULT_PROTOCOL}://{settings.DEFAULT_DOMAIN}/register/",
                settings.EMAIL_HOST_USER,
                [email_dest],
                fail_silently=True  # <--- Questo evita l'Internal Server Error
            )
            
            # Segna come inviato nel database
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ Segnale completato per {email_dest}")
            
    except Exception as e:
        print(f"❌ Errore nel segnale: {e}")

@receiver(post_save, sender=Payslip)
def notifica_nuovo_cedolino(sender, instance, created, **kwargs):
    if created:
        try:
            email = instance.employee.email_invio
            if email:
                send_mail(
                    "Nuovo Cedolino",
                    "È disponibile un nuovo documento.",
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=True
                )
        except Exception:
            pass