import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'tua_email@esempio.com', 'tua_password_sicura')
    print("Superuser creato con successo!")
else:
    print("Superuser già esistente.")