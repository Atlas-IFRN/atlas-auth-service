from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, Course, Institution, User


# Configuração personalizada para o Utilizador
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Campos que aparecerão na lista principal
    list_display = ('registration_number', 'first_name', 'role', 'course', 'ira', 'is_staff')
    # Filtros laterais
    list_filter = ('role', 'course', 'institution', 'is_staff')
    # Campos de pesquisa
    search_fields = ('registration_number', 'full_name', 'email')

    # Organização dos campos dentro do formulário de edição
    fieldsets = UserAdmin.fieldsets + (
        (
            'Academic Data',
            {'fields': ('registration_number', 'cpf', 'full_name', 'role', 'ira', 'period', 'institution', 'course')},
        ),
        ('Links Sociais', {'fields': ('linkedin', 'github', 'about_me')}),
    )


# Registos simples para as tabelas de apoio
@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'table_name', 'action', 'record_id', 'user_id', 'created_at')
    list_filter = ('table_name', 'action', 'created_at')
    search_fields = ('record_id', 'user_id')
    readonly_fields = ('id', 'table_name', 'action', 'record_id', 'user_id', 'payload', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
