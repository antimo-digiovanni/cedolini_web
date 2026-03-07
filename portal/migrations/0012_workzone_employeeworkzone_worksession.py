from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0011_backfill_registered_employees"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkZone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("radius_meters", models.PositiveIntegerField(default=100)),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="WorkSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("work_date", models.DateField(default=django.utils.timezone.localdate)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("start_latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("start_longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("end_latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("end_longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("start_within_zone", models.BooleanField(default=False)),
                ("end_within_zone", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_sessions", to="portal.employee"),
                ),
                (
                    "end_zone",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="end_sessions", to="portal.workzone"),
                ),
                (
                    "start_zone",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="start_sessions", to="portal.workzone"),
                ),
            ],
            options={
                "ordering": ["-work_date", "-created_at"],
                "unique_together": {("employee", "work_date")},
            },
        ),
        migrations.CreateModel(
            name="EmployeeWorkZone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("valid_from", models.DateField(default=django.utils.timezone.now)),
                ("valid_to", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "employee",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="zone_assignments", to="portal.employee"),
                ),
                (
                    "zone",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="employee_assignments", to="portal.workzone"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("employee", "zone", "valid_from")},
            },
        ),
    ]
