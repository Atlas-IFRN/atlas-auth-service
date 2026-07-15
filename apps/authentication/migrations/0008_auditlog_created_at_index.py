from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0007_auditlog_user_index'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['-created_at'],
                name='auth_audit_created_idx',
            ),
        ),
    ]
