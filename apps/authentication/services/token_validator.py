from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken


def validate_jwt(token: str) -> dict | None:
    """
    Valida o JWT usando o simplejwt e retorna o payload.
    Retorna None se o token for inválido ou expirado.
    """
    try:
        # UntypedToken valida assinatura + expiração
        validated = UntypedToken(token)
        return {
            "sub": str(validated["user_id"]),
            "role": validated.get("role", ""),
            "email": validated.get("email", ""),
        }
    except (InvalidToken, TokenError):
        return None
