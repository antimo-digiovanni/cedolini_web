from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0024_portalusersetting'),
    ]

    operations = [
        migrations.DeleteModel(
            name='SmartAgendaMessage',
        ),
        migrations.DeleteModel(
            name='SmartAgendaItem',
        ),
    ]