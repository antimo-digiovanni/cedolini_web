from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee, Payslip

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    """Invia email di benvenuto cercando l'email nel profilo o nell'utente."""
    try:
        # Cerchiamo l'email (prima nel campo email_invio, poi nell'utente Django)
        email_dest = instance.email_invio or (instance.user.email if instance.user else None)

        if not email_dest:
            print(f"⚠️ Nessun indirizzo trovato per {instance.full_name}.")
            return

        # Procediamo solo se NON è ancora stato inviato l'invito
        if not instance.invito_inviato:
            print(f"📧 --- Tentativo invio invito a: {email_dest} ---")
            
            send_mail(
                "Benvenuto nel Portale Cedolini - San Vincenzo",
                f"Ciao {instance.full_name},\n\nil tuo profilo è pronto. Registrati qui: {settings.DEFAULT_PROTOCOL}://{settings.DEFAULT_DOMAIN}/register/",
                settings.EMAIL_HOST_USER,
                [email_dest],
                fail_silently=False
            )
            
            # Segnamo come inviato per non spedirla più
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ Email inviata con successo!")
        else:
            print(f"ℹ️ Invito già inviato in precedenza a {email_dest}")

    except Exception as e:
        print(f"❌ ERRORE GMAIL: {e}")

@receiver(post_save, sender=Payslip)
def notifica_nuovo_cedolino(sender, instance, created, **kwargs):
    if created:
        try:
            email = instance.employee.email_invio or (instance.employee.user.email if instance.employee.user else None)
            if email:
                send_mail(
                    f"Nuovo Cedolino {instance.month:02d}/{instance.year}",
                    f"Ciao {instance.employee.full_name}, un nuovo cedolino è disponibile.",
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False
                )
        except Exception:
            pass