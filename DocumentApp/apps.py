import sys
from django.apps import AppConfig


class DocumentappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "DocumentApp"

    def ready(self):
        # Auto-migration automatique au démarrage / rechargement du serveur de développement
        if any("runserver" in arg for arg in sys.argv):
            try:
                from django.core.management import call_command
                call_command("migrate", "DocumentApp", interactive=False)
            except Exception:
                pass
