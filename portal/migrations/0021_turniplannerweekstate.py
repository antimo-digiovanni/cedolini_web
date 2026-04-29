from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


TURNI_PLANNER_GROUP_NAME = "turni_planner_users"


def create_turni_planner_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=TURNI_PLANNER_GROUP_NAME)


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0020_smartagendaitem_priority_daily_time"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TurniPlannerWeekState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("week_label", models.CharField(max_length=255, unique=True)),
                ("planner_data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_turni_planner_states", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at", "week_label"]},
        ),
        migrations.RunPython(create_turni_planner_group, migrations.RunPython.noop),
    ]
