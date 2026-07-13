from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    name = 'apps.authentication'

    def ready(self):
        # Registra os signals de invalidação do cache de perfil.
        from . import signals  # noqa: F401
