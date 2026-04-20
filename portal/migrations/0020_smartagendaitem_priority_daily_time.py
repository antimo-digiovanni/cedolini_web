from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0019_smartagendaitem_smartagendamessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='smartagendaitem',
            name='is_daily',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='smartagendaitem',
            name='priority',
            field=models.CharField(choices=[('low', 'Bassa'), ('normal', 'Normale'), ('high', 'Alta'), ('urgent', 'Urgente')], default='normal', max_length=20),
        ),
        migrations.AddField(
            model_name='smartagendaitem',
            name='remind_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name='smartagendaitem',
            options={'ordering': ['status', '-priority', 'remind_on', 'remind_time', '-created_at']},
        ),
    ]