import os
import django
from django.core.mail import send_mail

# Configura l'ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    print("Tentativo di invio email...")
    send_mail(
        'Test Portale Cedolini',
        'Se leggi questo, l\'invio email funziona!',
        'antimo.digiovanni@sanvincenzosrl.com',
        ['antimo.digiovanni@sanvincenzosrl.com'],
        fail_silently=False,
    )
    print("✅ Successo! L'email è stata inviata.")
except Exception as e:
    print(f"❌ Errore durante l'invio: {e}")