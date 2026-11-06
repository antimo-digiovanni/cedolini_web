from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .mark_anomalies import find
from .models import Employee, EmployeeWorkZone, WorkMarkRequest, WorkSession, WorkZone
from .views import _apply_approved_mark_request_to_session, _reconcile_overnight_sessions


class ForgotEntryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pietro")
        self.employee = Employee.objects.create(user=self.user, first_name="Pietro", last_name="Prova")
        self.admin = get_user_model().objects.create_user(username="capo", is_staff=True)
        zone = WorkZone.objects.create(name="Sede", latitude=40, longitude=14, radius_meters=200)
        EmployeeWorkZone.objects.create(employee=self.employee, zone=zone, valid_from=timezone.localdate() - timedelta(days=10))
        self.day = timezone.localdate()
        self.client.force_login(self.user)

    def at(self, hour, minute=0, day=None):
        return timezone.make_aware(datetime.combine(day or self.day, datetime.min.time())) + timedelta(hours=hour, minutes=minute)

    def post(self, ts, data):
        with patch("django.utils.timezone.now", return_value=ts):
            return self.client.post(reverse("timekeeping"), data)

    def test_exit_right_after_entry_is_refused(self):
        self.assertEqual(self.post(self.at(6, 17), {"action": "start"}).status_code, 200)
        response = self.post(self.at(6, 18), {"action": "end"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("meno di 5 minuti", response.json()["error"])
        self.assertIsNone(WorkSession.objects.get(employee=self.employee).ended_at)
        self.assertEqual(self.post(self.at(14, 0), {"action": "end"}).status_code, 200)

    def test_forgot_entry_same_day(self):
        response = self.post(self.at(15, 0), {"action": "end_forgot", "entry_time": "07:00"})
        self.assertEqual(response.status_code, 200, response.content)
        session = WorkSession.objects.get(employee=self.employee)
        self.assertIsNone(session.started_at)
        self.assertEqual(timezone.localtime(session.ended_at).hour, 15)
        req = WorkMarkRequest.objects.get(employee=self.employee)
        self.assertEqual(req.mark_type, WorkMarkRequest.MARK_TYPE_START)
        self.assertIn("oggi alle 07:00", req.reason)
        # finché la richiesta è in attesa non compare tra le marcature da sistemare
        self.assertEqual([r for r in find() if r["employee"] == self.employee], [])
        req.status = WorkMarkRequest.STATUS_APPROVED
        req.save()
        _apply_approved_mark_request_to_session(req)
        session.refresh_from_db()
        self.assertEqual(timezone.localtime(session.started_at).hour, 7)
        self.assertEqual(session.worked_minutes(), 480)

    def test_forgot_entry_night_shift(self):
        response = self.post(self.at(6, 15), {"action": "end_forgot", "entry_time": "22:05"})
        self.assertEqual(response.status_code, 200, response.content)
        req = WorkMarkRequest.objects.get(employee=self.employee)
        self.assertEqual(req.work_date, self.day - timedelta(days=1))
        self.assertIn("ieri alle 22:05", req.reason)
        req.status = WorkMarkRequest.STATUS_APPROVED
        req.save()
        _apply_approved_mark_request_to_session(req)
        _reconcile_overnight_sessions(employee=self.employee, start_date=self.day - timedelta(days=2), end_date=self.day)
        sessions = list(WorkSession.objects.filter(employee=self.employee).exclude(started_at=None, ended_at=None))
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].worked_minutes(), 8 * 60 + 10)

    def test_forgot_entry_rejects_bad_time(self):
        self.assertEqual(self.post(self.at(15, 0), {"action": "end_forgot", "entry_time": ""}).status_code, 400)
        self.assertEqual(self.post(self.at(15, 0), {"action": "end_forgot", "entry_time": "16:00"}).status_code, 400)  # ieri 16:00 = 23 ore
        self.assertFalse(WorkSession.objects.filter(employee=self.employee).exclude(ended_at=None).exists())

    def test_anomalies_listed_in_dashboard_todo(self):
        yesterday = self.day - timedelta(days=1)
        WorkSession.objects.create(employee=self.employee, work_date=yesterday, started_at=self.at(6, 17, yesterday), ended_at=self.at(6, 17, yesterday))
        two = self.day - timedelta(days=2)
        WorkSession.objects.create(employee=self.employee, work_date=two, sequence=1, started_at=self.at(6, 0, two))
        kinds = sorted(r["kind"] for r in find())
        self.assertEqual(kinds, ["no_exit", "short"])
        self.client.force_login(self.admin)
        page = self.client.get(reverse("admin_mark_anomalies"))
        self.assertContains(page, "Entrata e uscita nello stesso momento")
        self.assertContains(page, "Uscita mancante")
        from .admin_todo import admin_todo_items
        self.assertTrue(any(t["label"].startswith("Marcature da correggere") and t["count"] == 2 for t in admin_todo_items()))

    def test_exit_button_opens_forgot_panel_without_entry(self):
        page = self.client.get(reverse("timekeeping")).content.decode()
        button = page.split('id="btnEnd"', 1)[1].split(">", 1)[0]
        self.assertIn('data-no-entry="1"', button)
        self.assertNotIn("disabled", button)
        self.assertIn("forgotEntryPanel", page)


class CorrectAnomaliesTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="capo2", is_staff=True)
        u = get_user_model().objects.create_user(username="notte")
        self.employee = Employee.objects.create(user=u, first_name="Notte", last_name="Prova")
        self.client.force_login(self.admin)
        self.day = timezone.localdate() - timedelta(days=1)

    def at(self, day, hour, minute=0):
        return timezone.make_aware(datetime.combine(day, datetime.min.time())) + timedelta(hours=hour, minutes=minute)

    def fix(self, session, start, end):
        return self.client.post(reverse("admin_mark_anomalies"), {"session_id": session.pk, "start_time": start, "end_time": end})

    def test_short_night_shift_fixed_inline(self):
        s = WorkSession.objects.create(employee=self.employee, work_date=self.day, started_at=self.at(self.day, 6, 17), ended_at=self.at(self.day, 6, 17))
        page = self.client.get(reverse("admin_mark_anomalies"))
        self.assertContains(page, "Marcature da correggere")
        self.assertRedirects(self.fix(s, "22:05", "06:17"), reverse("admin_mark_anomalies"))
        s.refresh_from_db()
        self.assertEqual(s.effective_started_at(), self.at(self.day - timedelta(days=1), 22, 5))
        self.assertEqual(s.effective_ended_at(), self.at(self.day, 6, 17))
        self.assertEqual(s.worked_minutes(), 8 * 60 + 12)
        self.assertEqual([r for r in find() if r["employee"] == self.employee], [])

    def test_missing_exit_and_long_shift(self):
        two = self.day - timedelta(days=1)
        a = WorkSession.objects.create(employee=self.employee, work_date=two, started_at=self.at(two, 6, 0))
        self.fix(a, "06:00", "14:00")
        a.refresh_from_db()
        self.assertEqual(a.worked_minutes(), 480)
        self.assertIsNone(a.corrected_started_at)
        b = WorkSession.objects.create(employee=self.employee, work_date=self.day, sequence=1, started_at=self.at(self.day, 14, 52), ended_at=self.at(self.day + timedelta(days=1), 8, 15))
        self.fix(b, "14:52", "17:00")
        b.refresh_from_db()
        self.assertEqual(b.effective_started_at(), self.at(self.day, 14, 52))
        self.assertEqual(b.effective_ended_at(), self.at(self.day, 17, 0))

    def test_missing_entry_night(self):
        s = WorkSession.objects.create(employee=self.employee, work_date=self.day, ended_at=self.at(self.day, 6, 10))
        self.fix(s, "22:00", "06:10")
        s.refresh_from_db()
        self.assertEqual(s.effective_started_at(), self.at(self.day - timedelta(days=1), 22, 0))
        self.assertEqual(s.worked_minutes(), 8 * 60 + 10)

    def test_short_day_shift_keeps_exit_day(self):
        s = WorkSession.objects.create(employee=self.employee, work_date=self.day, started_at=self.at(self.day, 15, 3), ended_at=self.at(self.day, 15, 3))
        self.fix(s, "06:31", "15:03")
        s.refresh_from_db()
        self.assertEqual(s.effective_started_at(), self.at(self.day, 6, 31))
        self.assertEqual(s.effective_ended_at(), self.at(self.day, 15, 3))
