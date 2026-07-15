from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0006_remove_notification'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['user_id', '-created_at'],
                name='auth_audit_user_time_idx',
            ),
        ),
    ]
