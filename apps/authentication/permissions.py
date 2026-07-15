from rest_framework.permissions import BasePermission


class IsTeacher(BasePermission):
    """Permite acesso somente a usuários autenticados com papel de professor."""

    message = 'Apenas professores podem acessar este recurso.'

    def has_permission(self, request, view):
        user = request.user
        role = str(getattr(user, 'role', '') or '').upper()
        return bool(user and user.is_authenticated and role == 'TEACHER')
