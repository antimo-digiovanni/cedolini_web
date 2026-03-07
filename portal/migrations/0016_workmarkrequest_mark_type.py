from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0015_workmarkrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="workmarkrequest",
            name="mark_type",
            field=models.CharField(
                choices=[("start", "Entrata"), ("end", "Uscita"), ("both", "Entrata e uscita")],
                default="both",
                max_length=10,
            ),
        ),
    ]
