from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Employee, Payslip

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    if created:
        try:
            # Prendiamo la mail dall'utente
            user_email = instance.user.email if instance.user else None
            if user_email:
                send_mail(
                    "Benvenuto",
                    "Profilo creato.",
                    settings.EMAIL_HOST_USER,
                    [user_email],
                    fail_silently=True
                )
        except Exception:
            pass

@receiver(post_save, sender=Payslip)
def notifica_nuovo_cedolino(sender, instance, created, **kwargs):
    if created:
        try:
            user_email = instance.employee.user.email if instance.employee.user else None
            if user_email:
                send_mail(
                    "Nuovo Cedolino",
                    "Caricato nuovo file.",
                    settings.EMAIL_HOST_USER,
                    [user_email],
                    fail_silently=True
                )
        except Exception:
            pass