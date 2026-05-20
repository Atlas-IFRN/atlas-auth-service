import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser


class UserRole(models.TextChoices):
    STUDENT = 'STUDENT', _('Estudante')
    TEACHER = 'TEACHER', _('Professor')
    # Administradores com a flag is_superuser do Django

class NotificationType(models.TextChoices):
    SCHOLARSHIP = 'SCHOLARSHIP', _('Scholarship')
    EVALUATION = 'EVALUATION', _('Evaluation')
    SYSTEM = 'SYSTEM', _('System')

class Institution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cpf = models.CharField(max_length=14, unique=True)
    registration_number = models.CharField(max_length=14, unique=True)
    
    #AbstractUser já tem first_name, last_name e is_active nativamente.
    full_name = models.CharField(max_length=255)

    #Campos acadêmicos somente para alunos
    ira = models.FloatField(null=True, blank=True)
    period = models.IntegerField(null=True, blank=True)
    about_me = models.TextField(null=True, blank=True)
    linkedin = models.URLField(null=True, blank=True)
    github = models.URLField(null=True, blank=True)


    role = models.CharField(max_length=10, choices=UserRole.choices, default=UserRole.STUDENT)

    lattes_url = models.URLField(null=True, blank=True)

    institution = models.ForeignKey('Institution', on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.username   
    
class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    type = models.CharField(max_length=20, choices=NotificationType.choices)
    created_at = models.DateTimeField(auto_now_add=True)