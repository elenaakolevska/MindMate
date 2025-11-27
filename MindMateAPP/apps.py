from django.apps import AppConfig


class MindmateappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'MindMateAPP'

    def ready(self):
        """Import signals when app is ready"""
        import MindMateAPP.signals
