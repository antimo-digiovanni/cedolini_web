from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0030_portalusersetting_personal_asset_reimbursement_adjustment'),
    ]

    operations = [
        migrations.CreateModel(
            name='CorporateCardEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('occurred_on', models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ('operation_type', models.CharField(choices=[('top_up', 'Ricarica datore di lavoro'), ('expense', 'Spesa carta aziendale')], db_index=True, max_length=20)),
                ('category', models.CharField(max_length=80)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('balance_delta', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='corporate_card_entries', to='auth.user')),
            ],
            options={
                'ordering': ['-occurred_on', '-created_at', '-id'],
            },
        ),
    ]
