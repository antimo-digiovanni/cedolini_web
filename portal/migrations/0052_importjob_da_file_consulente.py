from django.db import migrations


def forwards(apps, schema_editor):
    """Porta nello Storico caricamenti gli import già fatti dal file del consulente."""
    AuditEvent = apps.get_model('portal', 'AuditEvent')
    ImportJob = apps.get_model('portal', 'ImportJob')
    for ev in AuditEvent.objects.filter(action='payslips_imported_from_lul').order_by('created_at'):
        m = ev.metadata or {}
        saved = int(m.get('saved') or 0)
        existing = int(m.get('already_present') or 0)
        left = int(m.get('left_out') or 0)
        name = m.get('file') or ''
        if ImportJob.objects.filter(error_message=f'File del consulente: {name}'.strip(),
                                    created_payslips=saved).exists():
            continue
        job = ImportJob.objects.create(total_files=saved + existing + left, processed_files=saved + existing,
                                       created_payslips=saved, skipped=existing + left, status='completed',
                                       error_message=f'File del consulente: {name}'.strip())
        ImportJob.objects.filter(pk=job.pk).update(created_at=ev.created_at)


class Migration(migrations.Migration):
    dependencies = [('portal', '0051_codice_fiscale')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
