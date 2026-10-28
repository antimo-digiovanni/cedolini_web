from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Announcement, AnnouncementRead, Employee


@override_settings(PUSH_ASYNC=False)
class AnnouncementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin', password='x', is_staff=True)
        self.u1 = User.objects.create_user('mario', password='x')
        self.e1 = Employee.objects.create(user=self.u1, first_name='Mario', last_name='Rossi', must_change_password=False, privacy_accepted=True)
        self.u2 = User.objects.create_user('luigi', password='x')
        self.e2 = Employee.objects.create(user=self.u2, first_name='Luigi', last_name='Verdi', must_change_password=False, privacy_accepted=True)

    def _publish(self, **extra):
        data = {'title': 'Chiusura ponte', 'body': 'Il 1 novembre siamo chiusi.', 'audience': 'all'}
        data.update(extra)
        self.client.force_login(self.admin)
        with mock.patch('portal.push.send_to_user') as send, self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(reverse('admin_announcements'), data)
        return r, send

    def test_publish_notifies_and_tracks_reads(self):
        r, send = self._publish()
        ann = Announcement.objects.get()
        self.assertEqual(send.call_count, 2)
        self.client.force_login(self.u1)
        self.assertContains(self.client.get(reverse('dashboard')), 'comunicazione')
        self.assertContains(self.client.get(reverse('employee_announcements')), 'Da leggere')
        self.client.post(reverse('employee_announcement_detail', args=[ann.id]))
        self.assertTrue(AnnouncementRead.objects.filter(announcement=ann, employee=self.e1).exists())
        self.assertContains(self.client.get(reverse('employee_announcement_detail', args=[ann.id])), 'Hai confermato la lettura')
        self.client.force_login(self.admin)
        page = self.client.get(reverse('admin_announcement_detail', args=[ann.id]))
        self.assertContains(page, 'Letta da 1 su 2')
        self.assertContains(page, 'Luigi Verdi')
        with mock.patch('portal.push.send_to_user') as send, self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse('admin_announcement_detail', args=[ann.id]), {'action': 'remind'})
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.args[0], self.u2)

    def test_targeted_only_visible_to_recipients(self):
        self._publish(audience='some', recipients=[self.e1.id])
        ann = Announcement.objects.get()
        self.client.force_login(self.u2)
        self.assertEqual(self.client.get(reverse('employee_announcement_detail', args=[ann.id])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('employee_announcements')), 'Chiusura ponte')

    def test_validation_and_permissions(self):
        r, _ = self._publish(title='')
        self.assertContains(r, 'Scrivi titolo e testo')
        r, _ = self._publish(audience='some')
        self.assertContains(r, 'almeno un destinatario')
        self.client.force_login(self.u1)
        self.assertEqual(self.client.get(reverse('admin_announcements')).status_code, 302)


class AnnouncementNotificationTextTests(TestCase):
    def test_preview_and_reminder(self):
        from .announcement_views import notification_text
        from .models import Announcement
        ann = Announcement(title='Chiusura uffici', body='Venerdì gli uffici resteranno chiusi per inventario. ' * 5)
        title, body = notification_text(ann)
        self.assertEqual(title, 'San Vincenzo · Chiusura uffici')
        self.assertTrue(body.split('\n')[0].endswith('…'))
        self.assertLessEqual(len(body.split('\n')[0]), 111)
        self.assertIn('Ho letto', body)
        title, body = notification_text(ann, again=True)
        self.assertEqual(title, 'Da leggere: Chiusura uffici')
