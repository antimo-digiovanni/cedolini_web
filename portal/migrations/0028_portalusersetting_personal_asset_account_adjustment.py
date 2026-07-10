from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0027_personalassetentry'),
    ]

    operations = [
        migrations.AddField(
            model_name='portalusersetting',
            name='personal_asset_account_adjustment',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
    ]
