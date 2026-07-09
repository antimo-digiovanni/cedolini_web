from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0026_clear_repackaging_product_catalog'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalAssetEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('occurred_on', models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ('operation_type', models.CharField(choices=[('income', 'Entrata'), ('expense', 'Uscita'), ('transfer_to_piggy_bank', 'Trasferimento conto -> salvadanaio'), ('transfer_to_account', 'Trasferimento salvadanaio -> conto'), ('reimbursable_expense', 'Spesa rimborsabile'), ('reimbursement_received', 'Rimborso ricevuto'), ('advance_received', 'Anticipo ricevuto'), ('advance_returned', 'Anticipo restituito')], db_index=True, max_length=40)),
                ('category', models.CharField(max_length=80)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('reimbursement_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('account_delta', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('piggy_bank_delta', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('reimbursement_delta', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('advance_delta', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='personal_asset_entries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-occurred_on', '-created_at', '-id'],
            },
        ),
    ]