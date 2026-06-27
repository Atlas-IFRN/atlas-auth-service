from rest_framework import serializers

from .models import Notification, User


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


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Apenas campos sociais editáveis pelo próprio usuário via PATCH /me/."""

    class Meta:
        model = User
        fields = ['about_me', 'linkedin', 'github']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'type', 'created_at']
