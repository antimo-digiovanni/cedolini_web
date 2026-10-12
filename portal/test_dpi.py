import base64
import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image, ImageDraw

from .models import DpiDelivery, Employee


def _sig(blank=False):
    img = Image.new('RGBA', (400, 160), (0, 0, 0, 0))
    if not blank:
        ImageDraw.Draw(img).line([(20, 100), (120, 40), (220, 110), (360, 50)], fill=(11, 42, 91, 255), width=4)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


class DpiDeliveryTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        self.admin = User.objects.create_user('admin', password='x', is_staff=True)
        user = User.objects.create_user('mario', password='x')
        self.emp = Employee.objects.create(user=user, first_name='Mario', last_name='Rossi')
        other = User.objects.create_user('luigi', password='x')
        self.other_emp = Employee.objects.create(user=other, first_name='Luigi', last_name='Verdi')
        self.url = reverse('admin_employee_dpi', args=[self.emp.id])

    def _post(self, **extra):
        data = {'item': ['pantaloni', 'guanti'], 'qty_pantaloni': '2', 'extra_label': ['Casco'], 'extra_qty': ['1'], 'signature': _sig()}
        data.update(extra)
        with override_settings(MEDIA_ROOT=self.media, STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage', 'OPTIONS': {'location': self.media}},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        }):
            return self.client.post(self.url, data)

    def test_non_staff_redirected(self):
        self.client.login(username='mario', password='x')
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_form_renders(self):
        self.client.login(username='admin', password='x')
        self.assertContains(self.client.get(self.url), 'Consegna DPI')

    def test_create_delivery_generates_pdf(self):
        self.client.login(username='admin', password='x')
        resp = self._post()
        self.assertEqual(resp.status_code, 302)
        d = DpiDelivery.objects.get()
        self.assertEqual([i['text'] for i in d.items], ['Guanti anti-taglio', 'n. 2 pantaloni', 'n. 1 casco'])
        with open(f'{self.media}/{d.pdf.name}', 'rb') as fh:
            head = fh.read(5)
        self.assertEqual(head, b'%PDF-')

    def test_requires_signature_and_items(self):
        self.client.login(username='admin', password='x')
        self.assertContains(self._post(signature=_sig(blank=True)), 'Firma mancante')
        self.assertContains(self._post(item=[], extra_label=[]), 'almeno un DPI')
        self.assertEqual(DpiDelivery.objects.count(), 0)

    def test_pdf_access_control(self):
        self.client.login(username='admin', password='x')
        self._post()
        d = DpiDelivery.objects.get()
        with override_settings(MEDIA_ROOT=self.media, STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage', 'OPTIONS': {'location': self.media}},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        }):
            self.assertEqual(self.client.get(reverse('open_dpi', args=[d.id])).status_code, 200)
            self.client.login(username='luigi', password='x')
            self.assertEqual(self.client.get(reverse('open_dpi', args=[d.id])).status_code, 403)
