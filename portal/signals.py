from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, **kwargs):
    # Usiamo un blocco che non può fallire
    try:
        email = instance.email_invio
        if email and not instance.invito_inviato:
            send_mail(
                "Benvenuto",
                "Il tuo profilo è pronto.",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=True
            )
            # Aggiorna il database direttamente
            sender.objects.filter(pk=instance.pk).update(invito_inviato=True)
    except:
        pass