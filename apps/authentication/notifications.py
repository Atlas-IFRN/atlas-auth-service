"""
Publicação de notificações (produtor de eventos).

As notificações foram extraídas para o notification-service, que é o dono do
consumo. Este módulo apenas PUBLICA o evento `notifications.create` na fila do
RabbitMQ (arquitetura event-driven) — sem HTTP e sem conhecer a API/DB do
notification-service. O worker do notification-service consome e persiste.

A publicação é best-effort: qualquer falha (broker fora, etc.) é apenas logada,
nunca propagada, para não interromper o fluxo de autenticação. O timeout curto
e `retry=False` garantem que um broker indisponível não segure o login.
"""
import logging
import uuid

from django.conf import settings

from config.celery import app as celery_app

logger = logging.getLogger(__name__)


def send_notification(user_id, title, message, notification_type="SYSTEM"):
    """Publica um evento de criação de notificação na fila (fire-and-forget).

    Gera um `event_id` por evento para idempotência: se o broker reentregar a
    mensagem, o notification-service deduplica em vez de gravar duplicado.
    """
    try:
        celery_app.send_task(
            "notifications.create",
            kwargs={
                "user_id": str(user_id),
                "title": title,
                "message": message,
                "type": notification_type,
                "event_id": str(uuid.uuid4()),
            },
            queue=settings.NOTIFICATIONS_QUEUE,
            retry=False,
        )
    except Exception:
        logger.exception(
            "Falha ao publicar notificação na fila para o usuário %s", user_id
        )
