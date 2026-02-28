from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee, Payslip

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    try:
        # Cerchiamo l'email (campo profilo o utente)
        email_dest = instance.email_invio or (instance.user.email if instance.user else None)
        
        if email_dest and not instance.invito_inviato:
            print(f"📧 --- Tentativo invio invito a: {email_dest} ---")
            send_mail(
                "Benvenuto nel Portale Cedolini",
                f"Ciao {instance.full_name}, il tuo profilo è pronto. Registrati qui: {settings.DEFAULT_PROTOCOL}://{settings.DEFAULT_DOMAIN}/register/",
                settings.EMAIL_HOST_USER,
                [email_dest],
                fail_silently=False
            )
            # Aggiorna senza far ripartire il segnale
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ Email inviata con successo!")
        elif not email_dest:
            print(f"⚠️ Nessuna email trovata per {instance.full_name}")
    except Exception as e:
        print(f"❌ Errore Gmail: {e}")

@receiver(post_save, sender=Payslip)
def notifica_nuovo_cedolino(sender, instance, created, **kwargs):
    if created:
        try:
            email_dest = instance.employee.email_invio or (instance.employee.user.email if instance.employee.user else None)
            if email_dest:
                send_mail(
                    f"Nuovo Cedolino {instance.month}/{instance.year}",
                    f"Ciao {instance.employee.full_name}, un nuovo cedolino è disponibile.",
                    settings.EMAIL_HOST_USER,
                    [email_dest],
                    fail_silently=False
                )
        except Exception:
            pass