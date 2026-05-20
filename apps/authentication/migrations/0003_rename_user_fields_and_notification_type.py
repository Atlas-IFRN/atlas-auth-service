from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_user_curriculo_lattes'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='matricula',
            new_name='registration_number',
        ),
        migrations.RenameField(
            model_name='user',
            old_name='curriculo_lattes',
            new_name='lattes_url',
        ),
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=models.CharField(choices=[('SCHOLARSHIP', _('Scholarship')), ('EVALUATION', _('Evaluation')), ('SYSTEM', _('System'))], max_length=20),
        ),
    ]