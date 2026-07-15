import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    STUDENT = 'STUDENT', _('Estudante')
    TEACHER = 'TEACHER', _('Professor')
    # Administradores com a flag is_superuser do Django


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

    # AbstractUser já tem first_name, last_name e is_active nativamente.
    full_name = models.CharField(max_length=255)

    # Foto de perfil (URL vinda do SUAP)
    image = models.URLField(max_length=500, null=True, blank=True)

    # Campos acadêmicos somente para alunos
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


class AuditAction(models.TextChoices):
    CREATE = 'CREATE', _('Create')
    UPDATE = 'UPDATE', _('Update')
    DELETE = 'DELETE', _('Delete')


class AuditLogTable(models.TextChoices):
    USER = 'user', _('User')
    INSTITUTION = 'institution', _('Institution')
    COURSE = 'course', _('Course')
    NOTIFICATION = 'notification', _('Notification')


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_name = models.CharField(max_length=100, choices=AuditLogTable.choices)
    action = models.CharField(max_length=10, choices=AuditAction.choices)
    record_id = models.UUIDField(help_text="PK do registro afetado")
    user_id = models.UUIDField(null=True, blank=True, help_text="UUID do usuário responsável pela operação")
    payload = models.JSONField(null=True, blank=True, help_text="Snapshot before/after do registro")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', '-created_at'], name='auth_audit_user_time_idx'),
            models.Index(fields=['-created_at'], name='auth_audit_created_idx'),
        ]

    def __str__(self):
        return f"[{self.action}] {self.table_name} ({self.record_id})"
