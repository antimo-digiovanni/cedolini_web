from django.conf import settings
from django.db import migrations, models


def create_settings_for_existing_users(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL.split('.')[0], settings.AUTH_USER_MODEL.split('.')[1])
    PortalUserSetting = apps.get_model('portal', 'PortalUserSetting')
    for user in User.objects.all().iterator():
        PortalUserSetting.objects.get_or_create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0023_employee_show_published_turni'),
    ]

    operations = [
        migrations.CreateModel(
            name='PortalUserSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('show_published_turni', models.BooleanField(default=True)),
                ('user', models.OneToOneField(on_delete=models.deletion.CASCADE, related_name='portal_setting', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(create_settings_for_existing_users, migrations.RunPython.noop),
    ]