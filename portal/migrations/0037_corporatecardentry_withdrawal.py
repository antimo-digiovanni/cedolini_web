from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0036_alter_personalassetentry_operation_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='corporatecardentry',
            name='operation_type',
            field=models.CharField(
                choices=[
                    ('top_up', 'Ricarica datore di lavoro'),
                    ('expense', 'Spesa carta aziendale'),
                    ('withdrawal', 'Prelievo allo sportello'),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
    ]