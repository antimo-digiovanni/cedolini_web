from django.apps import AppConfig

class PortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portal'

    def ready(self):
        # Importiamo i segnali quando l'app è pronta
        import portal.signals