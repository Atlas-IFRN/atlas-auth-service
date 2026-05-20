from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Institution, Course, Notification

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
        ('Academic Data', {'fields': ('registration_number', 'cpf', 'full_name', 'role', 'ira', 'period', 'institution', 'course')}),
        ('Links Sociais', {'fields': ('linkedin', 'github', 'about_me')}),
    )

# Registos simples para as tabelas de apoio
@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')