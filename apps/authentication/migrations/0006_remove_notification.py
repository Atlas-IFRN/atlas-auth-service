from django.db import migrations


class Migration(migrations.Migration):
    """Remove o modelo Notification do auth-service.

    As notificações passaram a viver no notification-service (schema
    `notification`, banco próprio). Esta migração apenas dropa a tabela local.
    """

    dependencies = [
        ('authentication', '0005_user_image'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Notification',
        ),
    ]
