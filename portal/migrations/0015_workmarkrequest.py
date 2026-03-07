from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0014_timesheet_corrections_and_strict_geofence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkMarkRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("work_date", models.DateField(default=django.utils.timezone.localdate)),
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
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_mark_requests", to="portal.employee"),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_work_mark_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
