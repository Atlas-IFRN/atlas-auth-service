from django.urls import path
from .views import SuapLoginUrlView, SuapCallbackView, LogoutView, UserProfileView, UserDetailView, NotificationListView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Rotas do SUAP (Fluxo de entrada)
    path('suap/login/', SuapLoginUrlView.as_view(), name='suap_login-url'),
    path('suap/callback/', SuapCallbackView.as_view(), name='suap_callback'),

    # Rotas de refresh (Renovação de sessão)
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Rotas de perfil
    path('users/me/', UserProfileView.as_view(), name='user_profile'),
    path('users/<str:matricula>/', UserDetailView.as_view(), name='user_detail'),

    # Rota de notificações
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    
    # Rota de logout
    path('logout/', LogoutView.as_view(), name='auth_logout'),
]