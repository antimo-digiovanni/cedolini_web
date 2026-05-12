from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0021_turniplannerweekstate"),
    ]

    operations = [
        migrations.AddField(
            model_name="turniplannerweekstate",
            name="visible_to_employees",
            field=models.BooleanField(default=False),
        ),
    ]
