from django.db import migrations
from django.utils import timezone


def mark_existing_employees_registered(apps, schema_editor):
    Employee = apps.get_model("portal", "Employee")
    now = timezone.now()

    # One-time backfill requested by business: mark existing employees as registered.
    Employee.objects.filter(privacy_accepted=False).update(
        privacy_accepted=True,
        privacy_accepted_at=now,
    )


def noop_reverse(apps, schema_editor):
    # Intentionally no reverse to avoid unmarking historical state.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0010_employee_privacy_acceptance"),
    ]

    operations = [
        migrations.RunPython(mark_existing_employees_registered, noop_reverse),
    ]
