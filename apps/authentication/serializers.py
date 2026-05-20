from rest_framework import serializers
from .models import User, Notification

class UserSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True, default=None)
    institution_name = serializers.CharField(source='institution.name', read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            'id', 
            'matricula', 
            'first_name',
            'full_name', 
            'email',  
            'role', 
            'ira', 
            'period', 
            'about_me', 
            'linkedin', 
            'github', 
            'curriculo_lattes',
            'course_name', 
            'institution_name'
        ]

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 
            'title', 
            'message', 
            'is_read', 
            'type', 
            'created_at'
        ]
