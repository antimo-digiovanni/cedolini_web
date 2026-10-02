from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .models import Employee, EmployeeWorkZone, VacationRequest, WorkMarkRequest, WorkSession, WorkZone
from .views import _apply_approved_mark_request_to_session


class MultipleTimekeepingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="multiple-marks")
        self.employee = Employee.objects.create(user=self.user, first_name="Mario", last_name="Test")
        self.admin = get_user_model().objects.create_user(username="marks-admin", is_staff=True)
        self.zone = WorkZone.objects.create(name="Sede", latitude=40, longitude=14, radius_meters=200)
        EmployeeWorkZone.objects.create(employee=self.employee, zone=self.zone)
        self.day = timezone.localdate()
        self.client.force_login(self.user)

    def mark(self, action, hour):
        timestamp = timezone.make_aware(datetime.combine(self.day, datetime.min.time())) + timedelta(hours=hour)
        with patch("django.utils.timezone.now", return_value=timestamp):
            return self.client.post(reverse("timekeeping"), {"action": action})

    def test_two_intervals_preserve_marks_and_exclude_break(self):
        for action, hour in [("start", 8), ("end", 12), ("start", 14), ("end", 18)]:
            response = self.mark(action, hour)
            self.assertEqual(response.status_code, 200, response.content)
        sessions = list(WorkSession.objects.filter(employee=self.employee).order_by("started_at"))
        self.assertEqual(len(sessions), 2)
        self.assertEqual(sum(session.worked_minutes() for session in sessions), 480)
        self.assertEqual(timezone.localtime(sessions[0].started_at).hour, 8)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_timekeeping"), {"month": self.day.month, "year": self.day.year})
        self.assertEqual(response.context["matrix_rows"][0]["month_total"], "08:00")
        self.assertContains(response, "08:00-12:00")
        self.assertContains(response, "14:00-18:00")
        response = self.client.get(reverse("admin_timekeeping"), {"employee": self.employee.pk})
        self.assertEqual(response.context["month_total"], "08:00")
        marked_rows = [row for row in response.context["rows"] if row.get("session_id")]
        self.assertEqual(len(marked_rows), 2)
        response = self.client.get(reverse("admin_timekeeping"), {"employee": self.employee.pk, "format": "csv"})
        self.assertIn("08:00;12:00;04:00", response.content.decode())
        self.assertIn("14:00;18:00;04:00", response.content.decode())

    def test_dashboard_hides_previous_month_vacation_requests(self):
        previous_day = self.day.replace(day=1) - timedelta(days=1)
        VacationRequest.objects.create(employee=self.employee, start_date=previous_day, end_date=previous_day, reason="Old vacation")
        current = VacationRequest.objects.create(employee=self.employee, start_date=self.day, end_date=self.day, reason="Current vacation")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(list(response.context["recent_vacation_requests"]), [current])

    def test_reentry_button_is_enabled_after_exit(self):
        self.mark("start", 8)
        self.mark("end", 12)
        for page in ("dashboard", "timekeeping"):
            response = self.client.get(reverse(page))
            self.assertContains(response, "Marcatura ordinaria")
            self.assertContains(response, "Marcatura fuori zona")
            self.assertContains(response, "Usare solo se sei fuori zona")
            self.assertNotContains(response, '<th scope="col">Ore</th>')
            self.assertNotContains(response, '<th>Totale</th>')
            button = response.content.decode().split('id="btnStart"', 1)[1].split(">", 1)[0]
            self.assertNotIn("disabled", button)

    def test_stale_page_cannot_close_a_new_interval(self):
        self.mark("start", 8)
        previous = WorkSession.objects.get(employee=self.employee)
        self.mark("end", 12)
        self.mark("start", 14)
        response = self.client.post(reverse("timekeeping"), {"action": "end", "session_id": previous.pk})
        self.assertEqual(response.status_code, 409)
        self.assertIsNone(WorkSession.objects.get(employee=self.employee, sequence=2).ended_at)

    def test_duplicate_entry_is_rejected(self):
        self.mark("start", 8)
        self.assertEqual(self.mark("start", 9).status_code, 400)
        self.assertEqual(WorkSession.objects.filter(employee=self.employee).count(), 1)

    def test_approved_outside_requests_are_applied_once_per_interval(self):
        requests = []
        for mark_type, hour in [("start", 8), ("end", 12), ("start", 14), ("end", 18)]:
            timestamp = timezone.make_aware(datetime.combine(self.day, datetime.min.time())) + timedelta(hours=hour)
            with patch("django.utils.timezone.now", return_value=timestamp):
                request = WorkMarkRequest.objects.create(
                    employee=self.employee, work_date=self.day, mark_type=mark_type,
                    reason="Lavoro fuori sede", status="approved",
                )
                _apply_approved_mark_request_to_session(request)
            requests.append(request)
        for request in requests:
            _apply_approved_mark_request_to_session(request)
        self.client.get(reverse("timekeeping"))
        sessions = WorkSession.objects.filter(employee=self.employee)
        self.assertEqual(sessions.count(), 2)
        self.assertEqual(sum(session.worked_minutes() for session in sessions), 480)

    def test_approved_outside_entry_does_not_bypass_gps_on_later_entry(self):
        EmployeeWorkZone.objects.filter(employee=self.employee).update(strict_geofence=True)
        started = timezone.make_aware(datetime.combine(self.day, datetime.min.time())) + timedelta(hours=8)
        with patch("django.utils.timezone.now", return_value=started):
            request = WorkMarkRequest.objects.create(
                employee=self.employee, work_date=self.day, mark_type="start",
                reason="Lavoro fuori sede", status="approved",
            )
            session = _apply_approved_mark_request_to_session(request)
        session.ended_at = started + timedelta(hours=4)
        session.save()
        self.assertEqual(self.mark("start", 14).status_code, 400)
        self.assertEqual(WorkSession.objects.filter(employee=self.employee).count(), 1)

    def test_overnight_exit_and_next_day_reentry(self):
        self.mark("start", 22)
        previous_day = self.day
        self.day += timedelta(days=1)
        self.assertEqual(self.mark("end", 6).status_code, 200)
        self.assertEqual(self.mark("start", 14).status_code, 200)
        previous = WorkSession.objects.get(employee=self.employee, work_date=previous_day)
        self.assertEqual(previous.worked_minutes(), 480)
        self.assertEqual(WorkSession.objects.filter(employee=self.employee).count(), 2)

    def test_admin_corrects_and_deletes_only_selected_interval(self):
        for action, hour in [("start", 8), ("end", 12), ("start", 14), ("end", 18)]:
            self.mark(action, hour)
        first, second = WorkSession.objects.filter(employee=self.employee).order_by("sequence")
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin_timekeeping"), {
            "action": "correct_day", "employee_id": self.employee.pk,
            "target_date": self.day.isoformat(), "session_id": second.pk,
            "start_time": "14:30", "end_time": "18:00", "note": "Orario verificato",
        })
        self.assertEqual(response.status_code, 302)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.worked_minutes(), 240)
        self.assertEqual(second.worked_minutes(), 210)
        response = self.client.post(reverse("admin_timekeeping"), {
            "action": "delete_marking", "employee_id": self.employee.pk,
            "target_date": self.day.isoformat(), "session_id": second.pk, "delete_target": "day",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(WorkSession.objects.filter(pk=first.pk).exists())
        self.assertFalse(WorkSession.objects.filter(pk=second.pk).exists())

    def test_excel_preserves_all_intervals_and_total(self):
        from openpyxl import load_workbook
        for action, hour in [("start", 8), ("end", 12), ("start", 14), ("end", 18)]:
            self.mark(action, hour)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_timekeeping"), {"employee": self.employee.pk, "format": "xlsx"})
        sheet = load_workbook(BytesIO(response.content)).active
        rows = list(sheet.values)
        self.assertTrue(any(row[2:5] == ("08:00", "12:00", "04:00") for row in rows))
        self.assertTrue(any(row[2:5] == ("14:00", "18:00", "04:00") for row in rows))
        self.assertTrue(any(row[0] == "Totale mese" and row[3] == "08:00" for row in rows))

    def test_current_vacation_is_visible_and_blocks_all_marking(self):
        vacation = VacationRequest.objects.create(
            employee=self.employee, start_date=self.day - timedelta(days=5),
            end_date=self.day + timedelta(days=2), reason="Ferie approvate", status="approved",
        )
        self.assertEqual(self.mark("start", 8).status_code, 400)
        for page in ("dashboard", "timekeeping"):
            response = self.client.post(reverse(page), {"action": "request_out_of_zone", "mark_type": "start", "reason": "Prova durante ferie"})
            self.assertIn("request_status=vacation", response.url)
        self.assertFalse(WorkMarkRequest.objects.exists())
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_timekeeping"))
        self.assertEqual(list(response.context["current_vacations"]), [vacation])
        self.assertContains(response, "In ferie oggi")
        self.assertContains(response, "FERIE")

    def test_admin_counts_people_not_intervals(self):
        for action, hour in [("start", 8), ("end", 12), ("start", 14), ("end", 18)]:
            self.mark(action, hour)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.context["entered_today_count"], 1)
        self.assertEqual(response.context["completed_today_count"], 1)
        self.assertEqual(response.context["incomplete_today_count"], 0)

    def test_multiple_outside_requests_can_wait_for_approval(self):
        for page in ("dashboard", "timekeeping"):
            WorkMarkRequest.objects.all().delete()
            for mark_type in ("start", "end", "start", "end"):
                response = self.client.post(reverse(page), {
                    "action": "request_out_of_zone", "mark_type": mark_type, "reason": "Servizio fuori sede",
                })
                self.assertIn("request_status=sent_", response.url)
            self.assertEqual(WorkMarkRequest.objects.count(), 4)
            response = self.client.post(reverse(page), {
                "action": "request_out_of_zone", "mark_type": "end", "reason": "Servizio fuori sede",
            })
            self.assertIn("request_status=already_pending", response.url)

    def test_out_of_order_approvals_pair_the_correct_times(self):
        requests = []
        for mark_type, hour in [("start", 8), ("end", 12), ("start", 14), ("end", 18)]:
            timestamp = timezone.make_aware(datetime.combine(self.day, datetime.min.time())) + timedelta(hours=hour)
            with patch("django.utils.timezone.now", return_value=timestamp):
                requests.append(WorkMarkRequest.objects.create(
                    employee=self.employee, work_date=self.day, mark_type=mark_type,
                    reason="Servizio fuori sede", status="approved",
                ))
        for index in (3, 1, 0, 2):
            _apply_approved_mark_request_to_session(requests[index])
        sessions = list(WorkSession.objects.filter(employee=self.employee).order_by("started_at"))
        self.assertEqual(len(sessions), 2)
        self.assertEqual([session.worked_minutes() for session in sessions], [240, 240])


class TimekeepingMigrationTests(TransactionTestCase):
    def test_existing_marks_and_approvals_survive_migration(self):
        old_target = [("portal", "0037_corporatecardentry_withdrawal")]
        new_target = [("portal", "0038_worksession_multiple_intervals")]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            old_apps = executor.loader.project_state(old_target).apps
            user = old_apps.get_model("auth", "User").objects.create(username="historical-worker")
            employee = old_apps.get_model("portal", "Employee").objects.create(
                user_id=user.pk, first_name="Historical", last_name="Worker",
            )
            started = timezone.now() - timedelta(hours=2)
            ended = timezone.now() - timedelta(hours=1)
            session = old_apps.get_model("portal", "WorkSession").objects.create(
                employee_id=employee.pk, work_date=timezone.localdate(),
                started_at=started, ended_at=ended, start_latitude="40.123456",
            )
            request = old_apps.get_model("portal", "WorkMarkRequest").objects.create(
                employee_id=employee.pk, work_date=session.work_date,
                mark_type="start", reason="Historical approval", status="approved",
            )
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            new_apps = executor.loader.project_state(new_target).apps
            preserved = new_apps.get_model("portal", "WorkSession").objects.get(pk=session.pk)
            linked = new_apps.get_model("portal", "WorkMarkRequest").objects.get(pk=request.pk)
            self.assertEqual(preserved.started_at, started)
            self.assertEqual(preserved.ended_at, ended)
            self.assertEqual(str(preserved.start_latitude), "40.123456")
            self.assertEqual(preserved.sequence, 1)
            self.assertEqual(linked.applied_session_id, preserved.pk)
            self.assertIsNotNone(linked.applied_at)
        finally:
            MigrationExecutor(connection).migrate(new_target)