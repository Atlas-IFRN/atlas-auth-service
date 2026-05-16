from django.urls import path
from .views import SuapLoginUrlView, SuapCallbackView, LogoutView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Rotas do SUAP (Fluxo de entrada)
    path('suap/login/', SuapLoginUrlView.as_view(), name='suap_login-url'),
    path('suap/callback/', SuapCallbackView.as_view(), name='suap_callback'),

    # Rotas de refresh (Renovação de sessão)
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Rota de logout
    path('logout/', LogoutView.as_view(), name='auth_logout'),

]