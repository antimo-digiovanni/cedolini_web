from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0033_corporatecardentry_receipt_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlannedCorporateCardExpense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('planned_on', models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ('category', models.CharField(max_length=80)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('receipt_image', models.FileField(blank=True, null=True, upload_to='corporate_card_receipts/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_entry', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='planned_expense', to='portal.corporatecardentry')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='planned_corporate_card_expenses', to='auth.user')),
            ],
            options={'ordering': ['planned_on', 'created_at', 'id']},
        ),
    ]
