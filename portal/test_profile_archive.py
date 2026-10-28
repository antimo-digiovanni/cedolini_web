import io
import zipfile
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import Cud, Employee, Payslip, PayslipView, WorkSession
from .test_hr_extras import _storage


def _jpeg(w=900, h=1200, color=(200, 120, 90)):
    buf = io.BytesIO()
    Image.new('RGB', (w, h), color).save(buf, 'JPEG')
    return buf.getvalue()


class ProfilePhotoTests(TestCase):
    def setUp(self):
        self.media = _storage(self)
        self.admin = User.objects.create_user('capo', password='x', is_staff=True)
        self.user = User.objects.create_user('mario', password='x', first_name='Mario', last_name='Rossi')
        self.emp = Employee.objects.create(user=self.user, first_name='Mario', last_name='Rossi', must_change_password=False)
        other = User.objects.create_user('luigi', password='x')
        self.other = Employee.objects.create(user=other, first_name='Luigi', last_name='Verdi', must_change_password=False)

    def test_upload_square_and_permissions(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('employee_profile')), 'Aggiungi una foto')
        r = self.client.post(reverse('employee_profile'), {'photo': SimpleUploadedFile('a.jpg', _jpeg(), 'image/jpeg')})
        self.assertTrue(r.json()['ok'])
        self.emp.refresh_from_db()
        self.assertTrue(self.emp.photo)
        r = self.client.get(reverse('profile_photo', args=[self.emp.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Image.open(io.BytesIO(r.content)).size, (512, 512))
        # il collega non la vede, l'amministrazione sì
        self.client.force_login(self.other.user)
        self.assertEqual(self.client.get(reverse('profile_photo', args=[self.emp.id])).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('profile_photo', args=[self.emp.id])).status_code, 200)

    def test_bad_file_and_remove(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse('employee_profile'), {'photo': SimpleUploadedFile('a.jpg', b'nope', 'image/jpeg')})
        self.assertEqual(r.status_code, 400)
        self.client.post(reverse('employee_profile'), {'photo': SimpleUploadedFile('a.jpg', _jpeg(), 'image/jpeg')})
        self.client.post(reverse('employee_profile'), {'action': 'remove'})
        self.emp.refresh_from_db()
        self.assertFalse(self.emp.photo)

    def test_topbar_avatar_links_to_profile(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('dashboard')), 'aria-label="Il mio profilo e foto"')


class ArchiveAndOverviewTests(TestCase):
    def setUp(self):
        self.media = _storage(self)
        self.admin = User.objects.create_user('capo', password='x', is_staff=True)
        self.user = User.objects.create_user('mario', password='x')
        self.emp = Employee.objects.create(user=self.user, first_name='Mario', last_name='Rossi', must_change_password=False)
        p = Payslip(employee=self.emp, year=2026, month=10)
        p.pdf.save('p.pdf', ContentFile(b'%PDF-1.4 cedolino'), save=True)
        PayslipView.objects.create(payslip=p)
        c = Cud(employee=self.emp, year=2026)
        c.pdf.save('c.pdf', ContentFile(b'%PDF-1.4 cud'), save=True)
        now = timezone.now()
        WorkSession.objects.create(employee=self.emp, work_date=timezone.localdate(), started_at=now - timedelta(hours=8),
                                   ended_at=now)

    def test_archive_lists_and_filters(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('admin_archive')).status_code, 302)
        self.client.force_login(self.admin)
        r = self.client.get(reverse('admin_archive'))
        self.assertContains(r, 'Cedolino · Ottobre 2026')
        self.assertContains(r, 'CUD 2026')
        r = self.client.get(reverse('admin_archive') + '?tipo=cud&dipendente=%d' % self.emp.id)
        self.assertNotContains(r, 'Cedolino · Ottobre 2026')
        self.assertContains(r, 'Scarica tutto (ZIP)')

    def test_zip(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('admin_archive_zip', args=[self.emp.id]))
        self.assertEqual(r.status_code, 200)
        names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
        self.assertIn('cedolini/2026-10.pdf', names)
        self.assertIn('cud/CUD-2026.pdf', names)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('admin_archive_zip', args=[self.emp.id])).status_code, 403)

    def test_employee_overview(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('admin_employee_detail', args=[self.emp.id]))
        self.assertContains(r, 'Presenze ultimi 28 giorni')
        self.assertContains(r, 'Giorni lavorati')
        self.assertContains(r, '8h 00m')
        self.assertContains(r, 'Tutti i documenti')

    def test_welcome_markup(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('dashboard')), "el.className = 'sv-wl'")
