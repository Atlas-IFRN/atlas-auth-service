import re
from urllib.parse import urlsplit

from rest_framework import serializers

from .models import AuditLog, User


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'table_name',
            'action',
            'record_id',
            'user_id',
            'payload',
            'created_at',
        ]
        read_only_fields = fields


GITHUB_USERNAME_PATTERN = re.compile(
    r'^(?!-)(?!.*--)[A-Za-z0-9-]{1,39}(?<!-)$'
)
LINKEDIN_USERNAME_PATTERN = re.compile(r'^(?!-)[A-Za-z0-9-]{3,100}(?<!-)$')


def canonical_social_profile_url(value, *, platform):
    if not value:
        return value

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise serializers.ValidationError('URL de perfil inválida.') from exc

    host = (parsed.hostname or '').lower()
    path_parts = [part for part in parsed.path.split('/') if part]
    has_unsafe_url_parts = (
        parsed.scheme != 'https'
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or bool(parsed.query)
        or bool(parsed.fragment)
    )

    if platform == 'github':
        is_expected_path = (
            host in {'github.com', 'www.github.com'} and len(path_parts) == 1
        )
        username = path_parts[0] if is_expected_path else ''
        if has_unsafe_url_parts or not GITHUB_USERNAME_PATTERN.fullmatch(username):
            raise serializers.ValidationError(
                'Informe apenas um perfil do GitHub no formato github.com/usuario.'
            )
        return f'https://github.com/{username}'

    is_expected_path = (
        host in {'linkedin.com', 'www.linkedin.com'}
        and len(path_parts) == 2
        and path_parts[0].lower() == 'in'
    )
    username = path_parts[1] if is_expected_path else ''
    if (
        has_unsafe_url_parts
        or not LINKEDIN_USERNAME_PATTERN.fullmatch(username)
        or 'linkedin' in username.lower()
    ):
        raise serializers.ValidationError(
            'Informe apenas um perfil do LinkedIn no formato linkedin.com/in/usuario.'
        )
    return f'https://www.linkedin.com/in/{username}'


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
    github = serializers.SerializerMethodField()
    linkedin = serializers.SerializerMethodField()

    def get_github(self, user):
        try:
            return canonical_social_profile_url(user.github, platform='github')
        except serializers.ValidationError:
            return None

    def get_linkedin(self, user):
        try:
            return canonical_social_profile_url(user.linkedin, platform='linkedin')
        except serializers.ValidationError:
            return None

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
            'registration_number',
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

    def validate_github(self, value):
        return canonical_social_profile_url(value, platform='github')

    def validate_linkedin(self, value):
        return canonical_social_profile_url(value, platform='linkedin')
