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
