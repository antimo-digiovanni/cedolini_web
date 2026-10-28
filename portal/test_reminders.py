from datetime import datetime, timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from . import reminders
from .models import Employee, ExitReminder, WorkSession


def at(day, hh, mm=0):
    return timezone.make_aware(datetime(2026, 11, day, hh, mm), timezone.get_current_timezone())


class ReminderWindowTests(TestCase):
    def test_bands(self):
        self.assertEqual(reminders.reminder_window(at(3, 5, 0)), (at(3, 17), at(3, 18)))
        self.assertEqual(reminders.reminder_window(at(3, 8, 59)), (at(3, 17), at(3, 18)))
        self.assertEqual(reminders.reminder_window(at(3, 12, 0)), (at(3, 22), at(3, 23)))
        self.assertEqual(reminders.reminder_window(at(3, 22, 0)), (at(4, 6), at(4, 7)))
        self.assertIsNone(reminders.reminder_window(at(3, 9, 30)))
        self.assertIsNone(reminders.reminder_window(at(3, 16, 0)))


class SendRemindersTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('mario')
        self.emp = Employee.objects.create(user=self.user, first_name='Mario', last_name='Rossi')

    def _session(self, start, end=None, seq=1):
        return WorkSession.objects.create(employee=self.emp, work_date=timezone.localtime(start).date(), sequence=seq,
                                          started_at=start, ended_at=end)

    def test_sent_once_inside_window_only(self):
        s = self._session(at(3, 6, 30))
        with mock.patch('portal.push.send_to_user', return_value=1) as send:
            self.assertEqual(reminders.send_due_exit_reminders(now=at(3, 16, 55)), 0)   # prima della finestra
            self.assertEqual(reminders.send_due_exit_reminders(now=at(3, 17, 2)), 1)    # dentro
            self.assertEqual(reminders.send_due_exit_reminders(now=at(3, 17, 30)), 0)   # già inviato
        self.assertEqual(send.call_count, 1)
        self.assertIn('06:30', send.call_args.kwargs['body'])
        self.assertTrue(ExitReminder.objects.filter(session=s).exists())

    def test_no_reminder_after_window_or_if_exit_marked(self):
        self._session(at(3, 6, 0), end=at(3, 15, 0))
        self._session(at(3, 12, 0), seq=2)
        with mock.patch('portal.push.send_to_user', return_value=1) as send:
            self.assertEqual(reminders.send_due_exit_reminders(now=at(3, 17, 10)), 0)  # uscita già marcata
            self.assertEqual(reminders.send_due_exit_reminders(now=at(3, 23, 10)), 0)  # finestra 22-23 finita
        send.assert_not_called()

    def test_night_shift_next_morning(self):
        self._session(at(3, 22, 15))
        with mock.patch('portal.push.send_to_user', return_value=0):
            self.assertEqual(reminders.send_due_exit_reminders(now=at(3, 23, 30)), 0)
            self.assertEqual(reminders.send_due_exit_reminders(now=at(4, 6, 5)), 1)

    def test_claim_once_per_interval(self):
        self.assertTrue(reminders._claim('x', 300))
        self.assertFalse(reminders._claim('x', 300))
