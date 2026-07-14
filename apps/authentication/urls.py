from django.conf import settings
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    DebugSetRoleView,
    InternalValidateView,
    LogoutView,
    SuapCallbackView,
    SuapLoginUrlView,
    UserDetailView,
    UserProfileView,
)

urlpatterns = [
    # Rotas do SUAP (Fluxo de entrada)
    path('suap/login/', SuapLoginUrlView.as_view(), name='suap_login-url'),
    path('suap/callback/', SuapCallbackView.as_view(), name='suap_callback'),

    # Rotas de refresh (Renovação de sessão)
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Validação interna usada pelo Nginx (auth_request) — não pública
    path('internal/validate/', InternalValidateView.as_view(), name='internal_validate'),

    # Rotas de perfil
    path('me/', UserProfileView.as_view(), name='user_me'),
    path('users/me/', UserProfileView.as_view(), name='user_profile'),  # alias mantido
    path('users/<str:matricula>/', UserDetailView.as_view(), name='user_detail'),

    # Rota de logout
    path('logout/', LogoutView.as_view(), name='auth_logout'),
]

# Rota de DEBUG: alterna o papel do usuário logado (professor/estudante) para
# testar funcionalidades restritas a docentes. Só é montada com DJANGO_DEBUG=True
# — nunca fica exposta em produção.
if settings.DEBUG:
    urlpatterns += [
        path('debug/set-role/', DebugSetRoleView.as_view(), name='debug_set_role'),
    ]
