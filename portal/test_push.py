import base64
import json
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import push
from .models import DpiDelivery, Employee, PushSubscription


def _fake_browser_keys():
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b'=').decode()
    return b64(pub), b64(b'0123456789abcdef')


class FakeResponse:
    def __init__(self, status):
        self.status_code = status
        self.text = ''
        self.headers = {}
        self.reason = 'Gone' if status == 410 else 'Created'


class PushTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin', password='x', is_staff=True)
        self.user = User.objects.create_user('mario', password='x')
        self.emp = Employee.objects.create(user=self.user, first_name='Mario', last_name='Rossi', must_change_password=False)
        p256dh, auth = _fake_browser_keys()
        self.sub_data = {'endpoint': 'https://fcm.googleapis.com/fcm/send/abc', 'keys': {'p256dh': p256dh, 'auth': auth}}

    def test_keys_generated_once(self):
        a = push.get_keys()
        b = push.get_keys()
        self.assertEqual(a, b)
        self.assertEqual(len(base64.urlsafe_b64decode(a[1] + '==')), 65)

    def test_subscribe_requires_login_and_saves(self):
        url = reverse('push_subscribe')
        self.assertEqual(self.client.post(url, json.dumps(self.sub_data), content_type='application/json').status_code, 302)
        self.client.login(username='mario', password='x')
        self.assertEqual(self.client.get(reverse('push_public_key')).status_code, 200)
        r = self.client.post(url, json.dumps(self.sub_data), content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PushSubscription.objects.get().user, self.user)
        bad = dict(self.sub_data, endpoint='http://evil')
        self.assertEqual(self.client.post(url, json.dumps(bad), content_type='application/json').status_code, 400)

    def test_send_dpi_triggers_encrypted_push(self):
        PushSubscription.objects.create(user=self.user, endpoint=self.sub_data['endpoint'], **self.sub_data['keys'])
        self.client.login(username='admin', password='x')
        with mock.patch('pywebpush.requests.post', return_value=FakeResponse(201)) as post:
            r = self.client.post(reverse('admin_dpi'), {'employee': self.emp.id, 'item': ['scarpe'], 'action': 'send'})
        self.assertIn('outcome=sent_push', r['Location'])
        self.assertEqual(post.call_count, 1)
        args, kwargs = post.call_args
        self.assertEqual(args[0], self.sub_data['endpoint'])
        self.assertTrue(kwargs['headers']['authorization'].startswith('vapid t='))
        self.assertEqual(kwargs['headers']['content-encoding'], 'aes128gcm')
        self.assertEqual(DpiDelivery.objects.get().notified_devices, 1)

    def test_expired_subscription_removed(self):
        PushSubscription.objects.create(user=self.user, endpoint=self.sub_data['endpoint'], **self.sub_data['keys'])
        with mock.patch('pywebpush.requests.post', return_value=FakeResponse(410)):
            n = push.send_to_user(self.user, title='t', body='b', url='/portal/')
        self.assertEqual(n, 0)
        self.assertFalse(PushSubscription.objects.exists())

    def test_send_without_subscription(self):
        self.client.login(username='admin', password='x')
        r = self.client.post(reverse('admin_dpi'), {'employee': self.emp.id, 'item': ['scarpe'], 'action': 'send'})
        self.assertIn('outcome=sent', r['Location'])
        self.assertNotIn('sent_push', r['Location'])

    def test_service_worker_has_push_handler(self):
        body = self.client.get(reverse('service_worker')).content.decode()
        self.assertIn("addEventListener('push'", body)
        self.assertIn("notificationclick", body)

    def test_employee_dashboard_shows_prompt(self):
        self.client.login(username='mario', password='x')
        self.assertContains(self.client.get(reverse('employee_dpi')), 'Attiva notifiche')


class PayslipCudPushTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('anna', password='x')
        self.emp = Employee.objects.create(user=self.user, first_name='Anna', last_name='Bianchi', must_change_password=False)
        p256dh, auth = _fake_browser_keys()
        PushSubscription.objects.create(user=self.user, endpoint='https://web.push.apple.com/abc', p256dh=p256dh, auth=auth)

    def _capture(self, fn):
        from django.test import override_settings
        with override_settings(PUSH_ASYNC=False), \
                mock.patch('pywebpush.requests.post', return_value=FakeResponse(201)) as post, \
                self.captureOnCommitCallbacks(execute=True):
            fn()
        return post

    def test_payslip_notification(self):
        from .models import Payslip
        p = Payslip.objects.create(employee=self.emp, year=2026, month=9, pdf='payslips/x.pdf')
        post = self._capture(lambda: push.notify_payslip(p))
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args[0][0], 'https://web.push.apple.com/abc')

    def test_cud_notification(self):
        from .models import Cud
        c = Cud.objects.create(employee=self.emp, year=2025, pdf='cud/x.pdf')
        post = self._capture(lambda: push.notify_cud(c))
        self.assertEqual(post.call_count, 1)

    def test_payslip_message_text(self):
        from .models import Payslip
        p = Payslip.objects.create(employee=self.emp, year=2026, month=9, pdf='payslips/x.pdf')
        with mock.patch('portal.push.notify_later') as later:
            push.notify_payslip(p)
        self.assertIn('settembre 2026', later.call_args.kwargs['body'])
        self.assertEqual(later.call_args.kwargs['url'], reverse('view_document', args=['cedolino', p.id]))


class AdminEmployeePushTests(TestCase):
    def test_admin_with_employee_profile_sees_prompt_and_pending(self):
        u = User.objects.create_user('antimo', password='x', is_staff=True)
        emp = Employee.objects.create(user=u, first_name='Antimo', last_name='Di Giovanni', must_change_password=False)
        DpiDelivery.objects.create(employee=emp, items=[{'label': 'Scarpe', 'qty': 1, 'text': 'Scarpe'}], status='pending')
        self.client.login(username='antimo', password='x')
        r = self.client.get(reverse('admin_dashboard'))
        self.assertContains(r, 'Attiva notifiche')
        self.assertContains(r, 'una consegna DPI')
        self.assertEqual(self.client.get(reverse('employee_dpi')).status_code, 200)

    def test_admin_without_employee_profile_no_prompt(self):
        User.objects.create_user('boss', password='x', is_staff=True)
        self.client.login(username='boss', password='x')
        self.assertNotContains(self.client.get(reverse('admin_dashboard')), 'Attiva notifiche')


class PushDiagnosticsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin', password='x', is_staff=True)
        self.user = User.objects.create_user('mario', password='x')
        self.emp = Employee.objects.create(user=self.user, first_name='Mario', last_name='Rossi', must_change_password=False)
        self.client.login(username='admin', password='x')

    def test_no_devices(self):
        r = self.client.post(reverse('admin_dpi'), {'employee': self.emp.id, 'action': 'test_push'})
        self.assertContains(r, 'non ha nessun dispositivo iscritto')

    def test_apple_error_is_shown_and_jwt_exp_under_24h(self):
        import time
        p256dh, auth = _fake_browser_keys()
        PushSubscription.objects.create(user=self.user, endpoint='https://web.push.apple.com/x', p256dh=p256dh, auth=auth)
        resp = FakeResponse(403); resp.reason = 'Forbidden'; resp.text = '{"reason":"BadJwtToken"}'
        with mock.patch('pywebpush.requests.post', return_value=resp) as post:
            r = self.client.post(reverse('admin_dpi'), {'employee': self.emp.id, 'action': 'test_push'})
        self.assertContains(r, 'BadJwtToken')
        self.assertContains(r, 'iPhone/Safari')
        token = post.call_args[1]['headers']['authorization'].split('t=')[1].split(',')[0]
        claims = json.loads(base64.urlsafe_b64decode(token.split('.')[1] + '=='))
        self.assertLess(claims['exp'] - time.time(), 24 * 3600)
        self.assertEqual(claims['aud'], 'https://web.push.apple.com')
        # invio DPI con iscrizione presente ma fallita -> messaggio dedicato
        with mock.patch('pywebpush.requests.post', return_value=resp):
            r = self.client.post(reverse('admin_dpi'), {'employee': self.emp.id, 'item': ['scarpe'], 'action': 'send'})
        self.assertIn('sent_push_failed', r['Location'])


class PushRecentDevicesTests(TestCase):
    def test_no_devices_lists_other_accounts(self):
        admin = User.objects.create_user('admin', password='x', is_staff=True)
        emp_user = User.objects.create_user('antimo.dip', password='x')
        emp = Employee.objects.create(user=emp_user, first_name='Antimo', last_name='Di Giovanni', must_change_password=False)
        p256dh, auth = _fake_browser_keys()
        PushSubscription.objects.create(user=admin, endpoint='https://web.push.apple.com/z', p256dh=p256dh, auth=auth)
        self.client.login(username='admin', password='x')
        r = self.client.post(reverse('admin_dpi'), {'employee': emp.id, 'action': 'test_push'})
        self.assertContains(r, 'account «antimo.dip»')
        self.assertContains(r, 'account «admin» (admin)')


class ServiceWorkerSyntaxTests(TestCase):
    def test_service_worker_is_valid_javascript(self):
        """Un errore di sintassi impedisce al telefono di installare il service worker (e quindi le notifiche)."""
        import shutil
        import subprocess
        import tempfile
        import unittest
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node non disponibile')
        body = self.client.get(reverse('service_worker')).content
        with tempfile.NamedTemporaryFile(suffix='.js') as fh:
            fh.write(body)
            fh.flush()
            result = subprocess.run([node, '--check', fh.name], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class ServiceWorkerDocumentsTests(TestCase):
    def test_documents_are_not_intercepted(self):
        body = self.client.get(reverse('service_worker')).content.decode()
        for prefix in ("'/portal/open/'", "'/portal/cud/'", "'/portal/dpi/'"):
            self.assertIn(prefix, body)
        # i prefissi devono corrispondere agli URL reali dei documenti
        self.assertTrue(reverse('open_payslip', args=[1]).startswith('/portal/open/'))
        self.assertTrue(reverse('open_cud', args=[1]).startswith('/portal/cud/'))
        self.assertTrue(reverse('open_dpi', args=[1]).startswith('/portal/dpi/'))


class DocumentViewerTests(TestCase):
    def setUp(self):
        import tempfile, shutil
        from django.core.files.base import ContentFile
        from django.test import override_settings
        from .models import Payslip, Cud
        from . import dpi
        self.media = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.media, True)
        ov = override_settings(MEDIA_ROOT=self.media, STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage', 'OPTIONS': {'location': self.media}},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        }, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
        ov.enable(); self.addCleanup(ov.disable)
        self.user = User.objects.create_user('mario', password='x')
        self.emp = Employee.objects.create(user=self.user, first_name='Mario', last_name='Rossi', must_change_password=False, privacy_accepted=True)
        other = User.objects.create_user('luigi', password='x')
        Employee.objects.create(user=other, first_name='Luigi', last_name='Verdi', must_change_password=False, privacy_accepted=True)
        import datetime
        from .test_dpi import _sig
        pdf = dpi.build_pdf(employee_name='Mario Rossi', delivered_on=datetime.date(2026, 1, 1),
                            items=[{'label': 'Scarpe', 'qty': 1, 'text': 'Scarpe'}], signature_png=dpi.decode_signature(_sig()))
        self.p = Payslip(employee=self.emp, year=2026, month=1); self.p.pdf.save('ced.pdf', ContentFile(pdf))
        self.c = Cud(employee=self.emp, year=2025); self.c.pdf.save('cud.pdf', ContentFile(pdf))

    def test_viewer_has_buttons_pages_and_tracks_view(self):
        from .models import PayslipView
        self.client.login(username='mario', password='x')
        r = self.client.get(reverse('view_document', args=['cedolino', self.p.id]))
        self.assertContains(r, 'Cedolino Gennaio 2026')
        self.assertContains(r, 'Indietro'); self.assertContains(r, 'Scarica'); self.assertContains(r, 'Condividi')
        self.assertContains(r, reverse('document_page_image', args=['cedolino', self.p.id, 2]))
        self.assertTrue(PayslipView.objects.filter(payslip=self.p).exists())
        img = self.client.get(reverse('document_page_image', args=['cedolino', self.p.id, 1]))
        self.assertEqual(img['Content-Type'], 'image/png')
        self.assertTrue(img.content.startswith(b'\x89PNG'))
        self.assertEqual(self.client.get(reverse('document_page_image', args=['cedolino', self.p.id, 9])).status_code, 404)
        dl = self.client.get(reverse('open_payslip', args=[self.p.id]) + '?download=1&src=viewer')
        self.assertTrue(dl['Content-Disposition'].startswith('attachment'))
        self.assertContains(self.client.get(reverse('view_document', args=['cud', self.c.id])), 'CUD 2025')

    def test_other_employee_forbidden(self):
        self.client.login(username='luigi', password='x')
        self.assertEqual(self.client.get(reverse('view_document', args=['cedolino', self.p.id])).status_code, 403)
        self.assertEqual(self.client.get(reverse('document_page_image', args=['cud', self.c.id, 1])).status_code, 403)
        self.assertEqual(self.client.get(reverse('view_document', args=['altro', self.p.id])).status_code, 404)

    def test_dashboard_links_point_to_viewer(self):
        self.client.login(username='mario', password='x')
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, reverse('view_document', args=['cedolino', self.p.id]))


class NotifySheetTests(TestCase):
    def test_sheet_on_app_pages_for_logged_users_only(self):
        user = User.objects.create_user('luigi', password='x')
        Employee.objects.create(user=user, first_name='Luigi', last_name='Verdi', must_change_password=False)
        self.assertNotContains(self.client.get(reverse('login')), 'id="notifySheet"')
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard'))
        self.assertContains(resp, 'id="notifySheet"')
        self.assertContains(resp, 'Vuoi attivare le notifiche?')


class AdminNotificationsPageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('capo', password='x', is_staff=True)
        u1 = User.objects.create_user('anna', password='x')
        u2 = User.objects.create_user('bruno', password='x')
        self.e1 = Employee.objects.create(user=u1, first_name='Anna', last_name='Bianchi', must_change_password=False)
        self.e2 = Employee.objects.create(user=u2, first_name='Bruno', last_name='Neri', must_change_password=False)
        p256dh, auth = _fake_browser_keys()
        PushSubscription.objects.create(user=u1, endpoint='https://web.push.apple.com/x', p256dh=p256dh, auth=auth)

    def test_staff_only(self):
        self.client.force_login(self.e1.user)
        self.assertEqual(self.client.get(reverse('admin_notifications')).status_code, 302)

    def test_lists_active_and_inactive(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('admin_notifications'))
        self.assertContains(r, 'Anna Bianchi')
        self.assertContains(r, 'Bruno Neri')
        self.assertContains(r, 'iPhone/Safari')
        self.assertEqual(r.context['counts'], {'attive': 1, 'non_attive': 1, 'tutti': 2})
        r = self.client.get(reverse('admin_notifications') + '?filtro=non_attive')
        self.assertNotContains(r, 'Anna Bianchi')
        self.assertContains(r, 'Bruno Neri')

    def test_send_test_notification(self):
        self.client.force_login(self.admin)
        with mock.patch.object(push, 'send_to_user', return_value=1) as send:
            r = self.client.post(reverse('admin_notifications'), {'action': 'test', 'employee': self.e1.id})
        send.assert_called_once()
        self.assertContains(r, 'Notifica di prova inviata')
