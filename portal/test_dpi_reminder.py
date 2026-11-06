from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import DPI_STATUS_PENDING, DPI_STATUS_SIGNED, AuditEvent, DpiDelivery, Employee


class DpiReminderTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin', password='x', is_staff=True)
        self.emps = []
        for name in ('mario', 'luigi', 'anna'):
            u = User.objects.create_user(name, password='x')
            self.emps.append(Employee.objects.create(user=u, first_name=name.title(), last_name='Prova', must_change_password=False))
        items = [{'key': 'guanti', 'text': 'Guanti', 'qty': 1}]
        self.d1 = DpiDelivery.objects.create(employee=self.emps[0], items=items, status=DPI_STATUS_PENDING)
        self.d2 = DpiDelivery.objects.create(employee=self.emps[0], items=items, status=DPI_STATUS_PENDING)
        self.d3 = DpiDelivery.objects.create(employee=self.emps[1], items=items, status=DPI_STATUS_PENDING)
        DpiDelivery.objects.create(employee=self.emps[2], items=items, status=DPI_STATUS_SIGNED)
        self.client.force_login(self.admin)
        self.url = reverse('admin_dpi')

    def test_button_shown_only_with_pending(self):
        self.assertContains(self.client.get(self.url), 'Invia promemoria a tutti')
        DpiDelivery.objects.filter(status=DPI_STATUS_PENDING).update(status=DPI_STATUS_SIGNED)
        self.assertNotContains(self.client.get(self.url), 'Invia promemoria a tutti')

    def test_remind_all_one_push_per_employee(self):
        with patch('portal.push.send_to_user', side_effect=lambda user, **m: 1 if user.username == 'mario' else 0) as send:
            r = self.client.post(self.url, {'action': 'remind'})
        self.assertEqual(send.call_count, 2)
        users = {c.args[0].username: c.kwargs for c in send.call_args_list}
        self.assertEqual(set(users), {'mario', 'luigi'})
        self.assertIn('2 consegne', users['mario']['body'])
        self.assertEqual(users['luigi']['url'], reverse('employee_dpi_sign', args=[self.d3.id]))
        page = self.client.get(r['Location'])
        self.assertContains(page, 'la notifica è arrivata a 1 dipendente su 2')
        self.assertEqual(AuditEvent.objects.filter(action='dpi_reminder_sent').count(), 2)

    def test_remind_single(self):
        with patch('portal.push.send_to_user', return_value=1) as send:
            self.client.post(self.url, {'action': 'remind', 'delivery_id': self.d3.id})
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.args[0].username, 'luigi')

    def test_staff_only(self):
        self.client.force_login(self.emps[0].user)
        with patch('portal.push.send_to_user') as send:
            self.client.post(self.url, {'action': 'remind'})
        send.assert_not_called()
