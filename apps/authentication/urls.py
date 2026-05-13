from django.urls import path
from .views import SuapLoginUrlView, SuapCallbackView

urlpatterns = [
    path('suap/login/', SuapLoginUrlView.as_view(), name='suap-login-url'),
    path('suap/callback/', SuapCallbackView.as_view(), name='suap-callback'),
]