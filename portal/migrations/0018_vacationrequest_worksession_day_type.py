from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("portal", "0017_workzone_shape_and_rectangle_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="worksession",
            name="day_type",
            field=models.CharField(
                choices=[("work", "Lavoro"), ("vacation", "Ferie")],
                default="work",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="VacationRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField(default=django.utils.timezone.localdate)),
                ("end_date", models.DateField(default=django.utils.timezone.localdate)),
                ("reason", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "In attesa"), ("approved", "Approvata"), ("rejected", "Rifiutata")],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("review_note", models.CharField(blank=True, max_length=255, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vacation_requests", to="portal.employee"),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_vacation_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]