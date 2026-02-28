from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Employee

@receiver(post_save, sender=Employee)
def test_segnale(sender, instance, **kwargs):
    # Questo non fa nulla, serve solo a vedere se il sito smette di crashare
    print(f"Salvataggio intercettato per {instance.full_name}")