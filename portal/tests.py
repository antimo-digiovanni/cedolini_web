from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .access import TODAY_MARKINGS_GROUP_NAME
from .models import Employee, VacationRequest, WorkSession


class EmailOrUsernameBackendTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="mario.rossi",
			email="mario.rossi@example.com",
			password="Password123!",
		)

	def test_login_with_username(self):
		logged_user = authenticate(username="mario.rossi", password="Password123!")
		self.assertIsNotNone(logged_user)
		self.assertEqual(logged_user.pk, self.user.pk)

	def test_login_with_email(self):
		logged_user = authenticate(username="mario.rossi@example.com", password="Password123!")
		self.assertIsNotNone(logged_user)
		self.assertEqual(logged_user.pk, self.user.pk)

	def test_login_with_username_case_insensitive(self):
		logged_user = authenticate(username="Mario.Rossi", password="Password123!")
		self.assertIsNotNone(logged_user)
		self.assertEqual(logged_user.pk, self.user.pk)


class TodayMarkingsAccessTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.group = Group.objects.create(name=TODAY_MARKINGS_GROUP_NAME)
		self.owner_user = get_user_model().objects.create_user(
			username="titolare",
			password="Password123!",
			first_name="Mario",
			last_name="Bianchi",
		)
		self.owner_user.groups.add(self.group)

		self.employee_user = get_user_model().objects.create_user(
			username="dipendente",
			password="Password123!",
		)
		self.employee = Employee.objects.create(
			user=self.employee_user,
			first_name="Luca",
			last_name="Verdi",
		)
		WorkSession.objects.create(
			employee=self.employee,
			work_date=timezone.localdate(),
			started_at=timezone.now(),
		)

	def test_home_redirects_limited_user_to_today_markings(self):
		self.client.force_login(self.owner_user)
		response = self.client.get(reverse("home"))
		self.assertRedirects(response, reverse("today_markings_dashboard"))

	def test_dashboard_redirects_limited_user_to_today_markings(self):
		self.client.force_login(self.owner_user)
		response = self.client.get(reverse("dashboard"))
		self.assertRedirects(response, reverse("today_markings_dashboard"))

	def test_admin_dashboard_redirects_limited_user_to_today_markings(self):
		self.client.force_login(self.owner_user)
		response = self.client.get(reverse("admin_dashboard"))
		self.assertRedirects(response, reverse("today_markings_dashboard"))

	def test_limited_user_can_view_today_markings_page(self):
		self.client.force_login(self.owner_user)
		response = self.client.get(reverse("today_markings_dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Chi ha marcato oggi")
		self.assertContains(response, "Luca Verdi")

	def test_limited_user_can_view_previous_day_markings(self):
		WorkSession.objects.create(
			employee=self.employee,
			work_date=timezone.localdate() - timezone.timedelta(days=1),
			started_at=timezone.now() - timezone.timedelta(days=1),
		)
		self.client.force_login(self.owner_user)
		response = self.client.get(reverse("today_markings_dashboard"), {"date": (timezone.localdate() - timezone.timedelta(days=1)).isoformat()})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Elenco marcature del")
		self.assertContains(response, "Luca Verdi")


class VacationRequestFlowTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.employee_user = get_user_model().objects.create_user(
			username="operaio",
			password="Password123!",
		)
		self.employee = Employee.objects.create(
			user=self.employee_user,
			first_name="Giovanni",
			last_name="Neri",
		)
		self.admin_user = get_user_model().objects.create_user(
			username="admin",
			password="Password123!",
			is_staff=True,
		)

	def test_employee_can_submit_vacation_request_from_dashboard(self):
		self.client.force_login(self.employee_user)
		start_date = timezone.localdate() + timezone.timedelta(days=2)
		end_date = start_date + timezone.timedelta(days=1)

		response = self.client.post(
			reverse("dashboard"),
			{
				"action": "request_vacation",
				"start_date": start_date.isoformat(),
				"end_date": end_date.isoformat(),
				"vacation_reason": "Ferie programmate con la famiglia.",
			},
		)

		self.assertRedirects(response, f"{reverse('dashboard')}?vacation_status=sent")
		request_obj = VacationRequest.objects.get(employee=self.employee)
		self.assertEqual(request_obj.start_date, start_date)
		self.assertEqual(request_obj.end_date, end_date)
		self.assertEqual(request_obj.status, VacationRequest.STATUS_PENDING)

	def test_admin_dashboard_approval_marks_days_as_vacation_in_report(self):
		start_date = timezone.localdate() + timezone.timedelta(days=1)
		end_date = start_date + timezone.timedelta(days=1)
		request_obj = VacationRequest.objects.create(
			employee=self.employee,
			start_date=start_date,
			end_date=end_date,
			reason="Ferie gia concordate.",
		)

		self.client.force_login(self.admin_user)
		response = self.client.post(
			reverse("admin_dashboard"),
			{
				"action": "approve_vacation_request",
				"request_id": str(request_obj.id),
				"review_note": "Approvato",
			},
		)

		self.assertRedirects(response, reverse("admin_dashboard"))
		request_obj.refresh_from_db()
		self.assertEqual(request_obj.status, VacationRequest.STATUS_APPROVED)

		sessions = WorkSession.objects.filter(employee=self.employee, work_date__range=(start_date, end_date)).order_by("work_date")
		self.assertEqual(sessions.count(), 2)
		self.assertTrue(all(session.day_type == WorkSession.DAY_TYPE_VACATION for session in sessions))
		self.assertTrue(all(session.started_at is None and session.ended_at is None for session in sessions))

		report_response = self.client.get(
			reverse("admin_timekeeping"),
			{
				"employee": str(self.employee.id),
				"month": start_date.month,
				"year": start_date.year,
			},
		)
		self.assertEqual(report_response.status_code, 200)
		self.assertContains(report_response, "Ferie")
		self.assertContains(report_response, "FERIE")
