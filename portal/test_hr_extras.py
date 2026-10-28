import gzip
import json
import shutil
import tempfile
from datetime import date, timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (Announcement, DpiDelivery, Employee, EmployeeDeadline, IdentityDocument, VacationAllowance,
                     VacationRequest)
from .test_dpi import _sig


def _storage(test):
    media = tempfile.mkdtemp()
    test.addCleanup(shutil.rmtree, media, True)
    ov = override_settings(MEDIA_ROOT=media, STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage', 'OPTIONS': {'location': media}},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    })
    ov.enable()
    test.addCleanup(ov.disable)
    return media


class Base(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('capo', password='x', is_staff=True)
        self.user = User.objects.create_user('mario', password='x')
        self.emp = Employee.objects.create(user=self.user, first_name='Mario', last_name='Rossi', must_change_password=False)


class VacationTests(Base):
    def test_summary_counts_only_this_year_and_status(self):
        from .vacations import summary
        y = timezone.localdate().year
        self.assertIsNone(summary(self.emp, y))
        VacationAllowance.objects.create(employee=self.emp, year=y, days=26)
        VacationRequest.objects.create(employee=self.emp, start_date=date(y, 3, 1), end_date=date(y, 3, 5),
                                       reason='x', status='approved')
        VacationRequest.objects.create(employee=self.emp, start_date=date(y, 12, 30), end_date=date(y + 1, 1, 2),
                                       reason='x', status='approved')  # 2 giorni nell'anno
        VacationRequest.objects.create(employee=self.emp, start_date=date(y, 6, 1), end_date=date(y, 6, 2),
                                       reason='x', status='pending')
        VacationRequest.objects.create(employee=self.emp, start_date=date(y, 7, 1), end_date=date(y, 7, 9),
                                       reason='x', status='rejected')
        s = summary(self.emp, y)
        self.assertEqual((s['total'], s['approved'], s['pending'], s['left']), ('26', '7', '2', '19'))

    def test_admin_sets_allowance_and_employee_sees_it(self):
        y = timezone.localdate().year
        url = reverse('admin_set_vacation_allowance', args=[self.emp.id])
        self.client.force_login(self.user)
        self.client.post(url, {'year': y, 'days': '20'})
        self.assertFalse(VacationAllowance.objects.exists())  # solo staff
        self.client.force_login(self.admin)
        self.client.post(url, {'year': y, 'days': '26,5'})
        self.assertEqual(VacationAllowance.objects.get().days, 26.5)
        self.assertContains(self.client.get(reverse('admin_employee_detail', args=[self.emp.id])), 'Residue 26,5')
        r = self.client.post(url, {'year': y, 'days': 'abc'})
        self.assertIn('ferie_errore=1', r['Location'])
        self.client.force_login(self.user)
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, 'Residue')
        self.assertContains(r, 'id="vacCalendarData"')
        data = r.context['vacation_calendar']
        self.assertIn([12, 24], data['blocked'])

    def test_empty_value_removes_allowance(self):
        y = timezone.localdate().year
        VacationAllowance.objects.create(employee=self.emp, year=y, days=10)
        self.client.force_login(self.admin)
        self.client.post(reverse('admin_set_vacation_allowance', args=[self.emp.id]), {'year': y, 'days': ''})
        self.assertFalse(VacationAllowance.objects.exists())


class DeadlineTests(Base):
    def test_add_done_with_next_and_permissions(self):
        add = reverse('admin_add_deadline', args=[self.emp.id])
        due = timezone.localdate() + timedelta(days=10)
        self.client.force_login(self.user)
        self.client.post(add, {'kind': 'visita', 'title': 'Visita', 'due_date': due.isoformat()})
        self.assertFalse(EmployeeDeadline.objects.exists())
        self.client.force_login(self.admin)
        self.client.post(add, {'kind': 'visita', 'title': 'Visita medica annuale', 'due_date': due.isoformat()})
        dl = EmployeeDeadline.objects.get()
        self.assertContains(self.client.get(reverse('admin_deadlines') + '?filtro=scadenza'), 'Visita medica annuale')
        nxt = due + timedelta(days=365)
        self.client.post(reverse('admin_update_deadline', args=[dl.id]), {'action': 'done', 'next_due': nxt.isoformat()})
        dl.refresh_from_db()
        self.assertIsNotNone(dl.done_on)
        self.assertTrue(EmployeeDeadline.objects.filter(due_date=nxt, done_on__isnull=True).exists())
        r = self.client.post(add, {'kind': 'visita', 'title': '', 'due_date': ''})
        self.assertIn('scadenza_errore=1', r['Location'])

    def test_employee_sees_alert_and_notification_sent_once(self):
        from .deadlines import run_notifications
        EmployeeDeadline.objects.create(employee=self.emp, kind='formazione', title='Corso antincendio',
                                        due_date=timezone.localdate() + timedelta(days=5))
        EmployeeDeadline.objects.create(employee=self.emp, kind='formazione', title='Corso lontano',
                                        due_date=timezone.localdate() + timedelta(days=200))
        self.client.force_login(self.user)
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, 'Corso antincendio')
        self.assertNotContains(r, 'Corso lontano')
        self.assertContains(self.client.get(reverse('employee_documents')), 'Formazione e visite mediche')
        with mock.patch('portal.push.send_to_user', return_value=1) as send:
            self.assertEqual(run_notifications(), 1)
            self.assertEqual(run_notifications(), 0)
        self.assertTrue(send.called)

    def test_delete(self):
        dl = EmployeeDeadline.objects.create(employee=self.emp, title='X', due_date=timezone.localdate())
        self.client.force_login(self.admin)
        self.client.post(reverse('admin_update_deadline', args=[dl.id]), {'action': 'delete'})
        self.assertFalse(EmployeeDeadline.objects.exists())


class DpiArchiveTests(Base):
    def test_merged_pdf_of_signed_deliveries(self):
        _storage(self)
        self.client.force_login(self.admin)
        for _ in range(2):
            self.client.post(reverse('admin_dpi'), {'employee': str(self.emp.id), 'item': ['guanti'],
                                                    'action': 'sign_now', 'signature': _sig()})
        self.assertEqual(DpiDelivery.objects.filter(status='signed').count(), 2)
        r = self.client.get(reverse('admin_employee_dpi_archive', args=[self.emp.id]))
        self.assertEqual(r.status_code, 200)
        import fitz
        with fitz.open(stream=r.content, filetype='pdf') as doc:
            self.assertEqual(len(doc), 4)  # 2 pagine per consegna
        self.assertContains(self.client.get(reverse('admin_employee_detail', args=[self.emp.id])), 'Tutte le firmate in un PDF')
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('admin_employee_dpi_archive', args=[self.emp.id])).status_code, 403)


class AdminTodoAndHomeTests(Base):
    def test_admin_dashboard_todo(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('admin_dashboard')), 'Tutto in ordine')
        DpiDelivery.objects.create(employee=self.emp, items=[{'label': 'Scarpe', 'qty': 1, 'text': 'Scarpe'}], status='pending')
        Announcement.objects.create(title='T', body='B', all_employees=True, created_by=self.admin)
        r = self.client.get(reverse('admin_dashboard'))
        self.assertContains(r, 'Consegne DPI non ancora firmate')
        self.assertContains(r, 'Letture mancanti')

    def test_todo_ignores_superseded_pending_documents(self):
        from datetime import timedelta as _td

        from .admin_todo import admin_todo_items
        exp = timezone.localdate() + _td(days=800)
        old = IdentityDocument.objects.create(employee=self.emp, kind='ci', expiry_date=exp, status='pending',
                                              front_image='a.jpg', back_image='b.jpg')
        new = IdentityDocument.objects.create(employee=self.emp, kind='ci', expiry_date=exp, status='approved',
                                              front_image='c.jpg', back_image='d.jpg')
        IdentityDocument.objects.filter(id=old.id).update(uploaded_at=timezone.now() - _td(days=1))
        self.assertFalse([t for t in admin_todo_items() if 'Documenti' in t['label']])
        new.status = 'pending'
        new.save()
        item = next(t for t in admin_todo_items() if 'Documenti' in t['label'])
        self.assertEqual(item['count'], 1)

    def test_employee_home_tiles(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, 'aria-label="Accesso rapido"')
        self.assertContains(r, 'id="ferie-section"')


class BackupTests(Base):
    def test_backup_saved_and_old_removed(self):
        media = _storage(self)
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage

        from . import backup
        old = (timezone.localdate() - timedelta(days=40)).isoformat()
        default_storage.save(f'backup/db-{old}-abc.json.gz', ContentFile(b'x'))
        with mock.patch.object(backup, 'enabled', return_value=True):
            name = backup.run_backup()
        self.assertTrue(name.startswith('backup/db-'))
        with gzip.open(f'{media}/{name}') as fh:
            rows = json.load(fh)
        self.assertTrue(any(r['model'] == 'portal.employee' for r in rows))
        _, files = default_storage.listdir('backup')
        self.assertEqual(len(files), 1)

    def test_disabled_without_r2(self):
        from . import backup
        self.assertIsNone(backup.run_backup())
