from django.apps import AppConfig


class PollingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'polling'

    def ready(self):
        """
        Import signals when the app is ready
        """
        import polling.signals
