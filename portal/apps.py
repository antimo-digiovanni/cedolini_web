from django.apps import AppConfig

class PortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portal'

    def ready(self):
        # Importazione all'interno della funzione per evitare import circolari
        import portal.signals