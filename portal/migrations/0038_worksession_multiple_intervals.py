from django.db import migrations, models


def link_existing_approvals(apps, schema_editor):
    request_model = apps.get_model("portal", "WorkMarkRequest")
    session_model = apps.get_model("portal", "WorkSession")
    database = schema_editor.connection.alias
    for request in request_model.objects.using(database).filter(status="approved").iterator():
        session = session_model.objects.using(database).filter(
            employee_id=request.employee_id, work_date=request.work_date,
        ).first()
        if not session:
            continue
        has_start = request.mark_type not in {"start", "both"} or session.started_at is not None
        has_end = request.mark_type not in {"end", "both"} or session.ended_at is not None
        if has_start and has_end:
            request_model.objects.using(database).filter(pk=request.pk).update(
                applied_session_id=session.pk, applied_at=request.reviewed_at or request.created_at,
            )


class Migration(migrations.Migration):
    dependencies = [("portal", "0037_corporatecardentry_withdrawal")]

    operations = [
        migrations.AddField(
            model_name="worksession", name="sequence",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterUniqueTogether(
            name="worksession", unique_together={("employee", "work_date", "sequence")},
        ),
        migrations.AddField(
            model_name="workmarkrequest", name="applied_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workmarkrequest", name="applied_session",
            field=models.ForeignKey(
                to="portal.worksession", on_delete=models.SET_NULL, blank=True, null=True,
                related_name="mark_requests",
            ),
        ),
        migrations.RunPython(link_existing_approvals, migrations.RunPython.noop),
    ]