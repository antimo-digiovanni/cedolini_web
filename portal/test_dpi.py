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


class DpiTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        self.storage = override_settings(MEDIA_ROOT=self.media, STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage', 'OPTIONS': {'location': self.media}},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        })
        self.storage.enable()
        self.addCleanup(self.storage.disable)
        self.admin = User.objects.create_user('admin', password='x', is_staff=True)
        self.user = User.objects.create_user('mario', password='x')
        self.emp = Employee.objects.create(user=self.user, first_name='Mario', last_name='Rossi', must_change_password=False)
        other = User.objects.create_user('luigi', password='x')
        self.other_emp = Employee.objects.create(user=other, first_name='Luigi', last_name='Verdi', must_change_password=False)
        self.url = reverse('admin_dpi')

    def _post(self, **extra):
        data = {'employee': str(self.emp.id), 'item': ['pantaloni', 'guanti'], 'qty_pantaloni': '2',
                'extra_label': ['Casco'], 'extra_qty': ['1'], 'action': 'sign_now', 'signature': _sig()}
        data.update(extra)
        return self.client.post(self.url, data)

    def _pdf_head(self, d):
        with open(f'{self.media}/{d.pdf.name}', 'rb') as fh:
            return fh.read(5)

    def test_admin_page_only_staff(self):
        self.client.login(username='mario', password='x')
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.login(username='admin', password='x')
        self.assertContains(self.client.get(self.url), 'Storico consegne')

    def test_old_employee_url_redirects_with_preselection(self):
        self.client.login(username='admin', password='x')
        resp = self.client.get(reverse('admin_employee_dpi', args=[self.emp.id]))
        self.assertRedirects(resp, f'{self.url}?employee={self.emp.id}', fetch_redirect_response=False)

    def test_sign_now_generates_pdf(self):
        self.client.login(username='admin', password='x')
        self.assertEqual(self._post().status_code, 302)
        d = DpiDelivery.objects.get()
        self.assertEqual(d.status, 'signed')
        self.assertEqual(d.mode, 'in_person')
        self.assertEqual([i['text'] for i in d.items], ['Guanti anti-taglio', 'n. 2 pantaloni', 'n. 1 casco'])
        self.assertEqual(self._pdf_head(d), b'%PDF-')

    def test_validation(self):
        self.client.login(username='admin', password='x')
        self.assertContains(self._post(signature=_sig(blank=True)), 'Firma mancante')
        self.assertContains(self._post(item=[], extra_label=[]), 'almeno un DPI')
        self.assertContains(self._post(employee=''), 'Scegli il dipendente')
        self.assertEqual(DpiDelivery.objects.count(), 0)

    def test_send_to_employee_then_employee_signs(self):
        self.client.login(username='admin', password='x')
        self._post(action='send', signature='')
        d = DpiDelivery.objects.get()
        self.assertEqual(d.status, 'pending')
        self.assertFalse(d.pdf)

        # Il dipendente vede l'avviso e la voce nel menu.
        self.client.login(username='mario', password='x')
        self.assertContains(self.client.get(reverse('employee_dpi')), 'Firma consegna DPI')
        sign_url = reverse('employee_dpi_sign', args=[d.id])
        self.assertContains(self.client.get(sign_url), 'n. 2 pantaloni')

        # Firma vuota rifiutata, firma valida accettata.
        self.assertContains(self.client.post(sign_url, {'signature': _sig(blank=True)}), 'Firma mancante')
        self.client.post(sign_url, {'signature': _sig()}, REMOTE_ADDR='10.0.0.7')
        d.refresh_from_db()
        self.assertEqual(d.status, 'signed')
        self.assertEqual(d.mode, 'remote')
        self.assertEqual(d.signed_ip, '10.0.0.7')
        self.assertIsNotNone(d.signed_at)
        self.assertEqual(self._pdf_head(d), b'%PDF-')
        self.assertEqual(self.client.get(reverse('open_dpi', args=[d.id])).status_code, 200)

        # Già firmata: non si può rifirmare.
        self.assertRedirects(self.client.get(sign_url), reverse('employee_dpi'), fetch_redirect_response=False)

    def test_other_employee_cannot_see_or_sign(self):
        self.client.login(username='admin', password='x')
        self._post(action='send', signature='')
        d = DpiDelivery.objects.get()
        self.client.login(username='luigi', password='x')
        self.assertEqual(self.client.get(reverse('employee_dpi_sign', args=[d.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('employee_dpi_sign', args=[d.id]), {'signature': _sig()}).status_code, 404)
        self.assertEqual(self.client.get(reverse('open_dpi', args=[d.id])).status_code, 403)

    def test_cancel_pending(self):
        self.client.login(username='admin', password='x')
        self._post(action='send', signature='')
        d = DpiDelivery.objects.get()
        self.client.post(self.url, {'action': 'cancel', 'delivery_id': d.id})
        d.refresh_from_db()
        self.assertEqual(d.status, 'cancelled')
        self.client.login(username='mario', password='x')
        self.assertContains(self.client.get(reverse('employee_dpi')), 'Non hai consegne da firmare')
