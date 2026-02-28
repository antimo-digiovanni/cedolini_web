from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    try:
        # Prende l'email dal nuovo campo email_invio
        email_dest = instance.email_invio
        
        if email_dest and not instance.invito_inviato:
            send_mail(
                "Benvenuto nel Portale Cedolini",
                f"Ciao {instance.full_name}, il tuo profilo è pronto.",
                settings.EMAIL_HOST_USER,
                [email_dest],
                fail_silently=False
            )
            # Aggiorna il database per non inviarla più
            Employee.objects.filter(pk=instance.pk).update(invito_inviato=True)
            print(f"✅ MAIL INVIATA A {email_dest}")
    except Exception as e:
        print(f"❌ ERRORE: {e}")