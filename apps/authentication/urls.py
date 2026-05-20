from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LogoutView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationReadView,
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

    # Rotas de perfil
    path('me/', UserProfileView.as_view(), name='user_me'),
    path('users/me/', UserProfileView.as_view(), name='user_profile'),  # alias mantido
    path('users/<str:matricula>/', UserDetailView.as_view(), name='user_detail'),

    # Rotas de notificações
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/<uuid:notification_id>/read/', NotificationReadView.as_view(), name='notification_read'),
    path('notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),

    # Rota de logout
    path('logout/', LogoutView.as_view(), name='auth_logout'),
]
