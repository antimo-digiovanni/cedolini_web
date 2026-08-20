from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0031_corporatecardentry'),
    ]

    operations = [
        migrations.AddField(
            model_name='corporatecardentry',
            name='receipt_image',
            field=models.ImageField(blank=True, null=True, upload_to='corporate_card_receipts/'),
        ),
    ]
