import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# O auth-service é apenas PRODUTOR: publica o evento `notifications.create` na
# fila do notification-service. Não roda worker nem define tasks próprias — a
# app Celery existe só para o send_task encontrar o broker (RabbitMQ).
app = Celery("atlas_auth_service")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
