from rest_framework_simplejwt.authentication import JWTAuthentication

from .audit import set_current_actor_id


class AtlasJWTAuthentication(JWTAuthentication):
    """Autentica o usuário local e o identifica para os signals de auditoria."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            set_current_actor_id(result[0].id)
        return result
