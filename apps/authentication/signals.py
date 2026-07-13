"""Invalidação do cache de perfil.

O `UserDetailView` cacheia a resposta do usuário (chave por matrícula e por id).
Como o auth é a fonte da verdade, qualquer alteração no usuário — via PATCH de
perfil, novo login SUAP (que regrava nome/foto/vínculo) ou edição no admin —
dispara `post_save` e limpa as chaves daquele usuário. A próxima requisição
regenera com o dado novo. `post_delete` cobre remoções.
"""
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import User


def user_cache_keys(user):
    keys = [f"user:{user.id}"]
    if user.registration_number:
        keys.append(f"user:{user.registration_number}")
    return keys


@receiver(post_save, sender=User)
@receiver(post_delete, sender=User)
def invalidate_user_cache(sender, instance, **kwargs):
    cache.delete_many(user_cache_keys(instance))
