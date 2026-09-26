from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

	dependencies = [
		('portal', '0034_plannedcorporatecardexpense'),
	]

	operations = [
		migrations.AddField(
			model_name='corporatecardentry',
			name='cash_delivery_note',
			field=models.CharField(blank=True, default='', max_length=255),
		),
		migrations.AddField(
			model_name='corporatecardentry',
			name='payment_method',
			field=models.CharField(blank=True, choices=[('company_card', 'Carta aziendale'), ('cash_withdrawn', 'Contanti prelevati'), ('bank_transfer_other', 'Bonifico/altro')], default='', max_length=30),
		),
		migrations.AddField(
			model_name='plannedcorporatecardexpense',
			name='cash_delivery_note',
			field=models.CharField(blank=True, default='', max_length=255),
		),
		migrations.AddField(
			model_name='plannedcorporatecardexpense',
			name='payment_method',
			field=models.CharField(blank=True, choices=[('company_card', 'Carta aziendale'), ('cash_withdrawn', 'Contanti prelevati'), ('bank_transfer_other', 'Bonifico/altro')], default='', max_length=30),
		),
		migrations.AddField(
			model_name='portalusersetting',
			name='corporate_card_bank_balance',
			field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
		),
		migrations.AddField(
			model_name='portalusersetting',
			name='corporate_card_bank_balance_date',
			field=models.DateField(blank=True, null=True),
		),
		migrations.AddField(
			model_name='portalusersetting',
			name='corporate_card_bank_note',
			field=models.TextField(blank=True),
		),
		migrations.CreateModel(
			name='CorporateCardEntryChargeRefundDetail',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('detail_type', models.CharField(choices=[('charge', 'Addebito'), ('refund', 'Rimborso')], max_length=20)),
				('amount', models.DecimalField(decimal_places=2, max_digits=12)),
				('occurred_on', models.DateField(default=django.utils.timezone.localdate)),
				('note', models.CharField(blank=True, max_length=255)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('corporate_card_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='charge_refund_details', to='portal.corporatecardentry')),
			],
			options={
				'ordering': ['occurred_on', 'created_at', 'id'],
			},
		),
	]