from rest_framework import serializers

from .models import User


class ProfileSearchSerializer(serializers.ModelSerializer):
    """Payload enxuto para a busca global (dropdown do cabeçalho).

    Retorna só o necessário para exibir uma linha de perfil (nome, papel legível
    e instituição) e navegar até /perfil/{matricula}.
    """

    role_label = serializers.CharField(source='get_role_display', read_only=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = ['registration_number', 'full_name', 'image', 'role_label', 'institution_name']


class UserSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True, default=None)
    institution_name = serializers.CharField(source='institution.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            'id',
            'registration_number',
            'first_name',
            'full_name',
            'image',
            'email',
            'role',
            'ira',
            'period',
            'about_me',
            'linkedin',
            'github',
            'lattes_url',
            'course_name',
            'institution_name',
        ]


class PublicUserSerializer(UserSerializer):
    """Dados que podem ser exibidos a um aluno em perfis de terceiros."""

    class Meta(UserSerializer.Meta):
        fields = [
            'id',
            'first_name',
            'full_name',
            'image',
            'email',
            'role',
            'period',
            'about_me',
            'linkedin',
            'github',
            'lattes_url',
            'course_name',
            'institution_name',
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Apenas campos sociais editáveis pelo próprio usuário via PATCH /me/."""

    class Meta:
        model = User
        fields = ['about_me', 'linkedin', 'github']
