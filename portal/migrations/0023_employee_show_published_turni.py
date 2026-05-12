from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0022_turniplannerweekstate_visible_to_employees'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='show_published_turni',
            field=models.BooleanField(default=True),
        ),
    ]