from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Employee, EmployeeWorkZone, WorkMarkRequest, WorkSession, WorkZone
from .views import _apply_approved_mark_request_to_session


class RecoveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="mario")
        self.employee = Employee.objects.create(user=self.user, first_name="Mario", last_name="Prova")
        zone = WorkZone.objects.create(name="Sede", latitude=40, longitude=14, radius_meters=200)
        EmployeeWorkZone.objects.create(employee=self.employee, zone=zone, valid_from=timezone.localdate() - timedelta(days=10))
        self.today = timezone.localdate()
        self.client.force_login(self.user)

    def at(self, hour, minute=0, day=None):
        return timezone.make_aware(datetime.combine(day or self.today, datetime.min.time())) + timedelta(hours=hour, minutes=minute)

    def post(self, ts, data):
        with patch("django.utils.timezone.now", return_value=ts):
            return self.client.post(reverse("timekeeping"), data)

    def approve(self, req):
        req.status = WorkMarkRequest.STATUS_APPROVED
        req.save()
        return _apply_approved_mark_request_to_session(req)

    def test_forgot_exit_today(self):
        WorkSession.objects.create(employee=self.employee, work_date=self.today, started_at=self.at(7))
        r = self.post(self.at(19), {"action": "request_recovery", "mark_type": "end", "day": "oggi", "time": "16:30", "reason": "telefono scarico"})
        self.assertIn("recovery_sent", r["Location"])
        req = WorkMarkRequest.objects.get()
        self.assertTrue(req.is_recovery)
        self.assertEqual(timezone.localtime(req.requested_at).strftime("%H:%M"), "16:30")
        self.assertIn("Uscita dimenticata", req.reason)
        self.approve(req)
        s = WorkSession.objects.get()
        self.assertEqual(timezone.localtime(s.ended_at).strftime("%H:%M"), "16:30")

    def test_forgot_exit_yesterday(self):
        y = self.today - timedelta(days=1)
        WorkSession.objects.create(employee=self.employee, work_date=y, started_at=self.at(7, day=y))
        self.post(self.at(6, 50), {"action": "request_recovery", "mark_type": "end", "day": "ieri", "time": "16:00"})
        req = WorkMarkRequest.objects.get()
        self.assertEqual(req.work_date, y)
        self.approve(req)
        s = WorkSession.objects.get(work_date=y)
        self.assertEqual(timezone.localtime(s.ended_at), timezone.localtime(self.at(16, day=y)))

    def test_forgot_entry(self):
        self.post(self.at(9), {"action": "request_recovery", "mark_type": "start", "day": "oggi", "time": "07:05"})
        req = WorkMarkRequest.objects.get()
        self.approve(req)
        s = WorkSession.objects.get(employee=self.employee, started_at__isnull=False)
        self.assertEqual(timezone.localtime(s.started_at).strftime("%H:%M"), "07:05")

    def test_invalid_requests(self):
        r = self.post(self.at(9), {"action": "request_recovery", "mark_type": "start", "day": "oggi", "time": "10:00"})
        self.assertIn("recovery_future", r["Location"])
        r = self.post(self.at(9), {"action": "request_recovery", "mark_type": "start", "day": "oggi", "time": ""})
        self.assertIn("recovery_time", r["Location"])
        WorkSession.objects.update_or_create(employee=self.employee, work_date=self.today, sequence=1, defaults={"started_at": self.at(8)})
        r = self.post(self.at(9), {"action": "request_recovery", "mark_type": "end", "day": "oggi", "time": "07:00"})
        self.assertIn("recovery_before_start", r["Location"])
        self.assertFalse(WorkMarkRequest.objects.exists())

    def test_admin_sees_recovery_badge_and_todo(self):
        self.post(self.at(9), {"action": "request_recovery", "mark_type": "start", "day": "oggi", "time": "07:05"})
        admin = get_user_model().objects.create_superuser(username="capo", password="x")
        self.client.force_login(admin)
        page = self.client.get(reverse("admin_timekeeping"))
        self.assertContains(page, "Recupero · ore 07:05")
        from .admin_todo import admin_todo_items
        self.assertIn("Recuperi marcatura da approvare", [i["label"] for i in admin_todo_items()])

    def test_employee_page_shows_both_choices(self):
        page = self.client.get(reverse("timekeeping"))
        self.assertContains(page, "Recupera marcatura")
        self.assertContains(page, "Sono fuori zona")

    def test_exit_without_entry_needs_entry_first(self):
        r = self.post(self.at(18), {"action": "request_recovery", "mark_type": "end", "day": "oggi", "time": "16:00"})
        self.assertIn("recovery_need_start", r["Location"])
        self.assertFalse(WorkMarkRequest.objects.exists())
        # prima l'entrata, poi l'uscita: accettate entrambe
        self.post(self.at(18), {"action": "request_recovery", "mark_type": "start", "day": "oggi", "time": "07:00"})
        r = self.post(self.at(18, 1), {"action": "request_recovery", "mark_type": "end", "day": "oggi", "time": "16:00"})
        self.assertIn("recovery_sent", r["Location"])
        start, end = WorkMarkRequest.objects.order_by("id")
        self.approve(start)
        self.approve(end)
        s = WorkSession.objects.get(employee=self.employee, started_at__isnull=False)
        self.assertEqual(timezone.localtime(s.ended_at).strftime("%H:%M"), "16:00")
        self.assertEqual(s.worked_minutes(), 540)
