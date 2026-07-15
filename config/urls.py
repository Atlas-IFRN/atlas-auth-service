from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(request):
    return HttpResponse("OK", status=200)


urlpatterns = [
    path('api/auth/admin/', admin.site.urls),
    path('health/', health_check),

    # Endpoint /metrics para o Prometheus (django-prometheus).
    path('', include('django_prometheus.urls')),

    path('api/auth/', include('apps.authentication.urls')),

    path('api/auth/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/auth/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
