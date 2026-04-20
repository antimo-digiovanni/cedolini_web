from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0018_vacationrequest_worksession_day_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SmartAgendaItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('note', models.TextField(blank=True)),
                ('source_text', models.TextField(blank=True)),
                ('remind_on', models.DateField(blank=True, null=True)),
                ('quoted_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('status', models.CharField(choices=[('open', 'Aperto'), ('done', 'Completato')], default='open', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='smart_agenda_items', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['status', 'remind_on', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SmartAgendaMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', 'Utente'), ('assistant', 'Assistente')], max_length=20)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='smart_agenda_messages', to=settings.AUTH_USER_MODEL)),
                ('related_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages', to='portal.smartagendaitem')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]