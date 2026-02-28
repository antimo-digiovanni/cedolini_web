from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Employee

@receiver(post_save, sender=Employee)
def invia_invito_registrazione(sender, instance, created, **kwargs):
    # Non facciamo più nulla qui perché inviamo il link manualmente
    # Questo evita i "timeout" di rete su Render
    print(f"DEBUG: Dipendente {instance.full_name} salvato. Link pronto in Admin.")