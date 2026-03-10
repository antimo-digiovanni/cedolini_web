from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0016_workmarkrequest_mark_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="workzone",
            name="shape",
            field=models.CharField(
                choices=[("circle", "Cerchio"), ("rect", "Rettangolo")],
                default="circle",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="workzone",
            name="rect_north",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="workzone",
            name="rect_south",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="workzone",
            name="rect_east",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="workzone",
            name="rect_west",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
    ]
