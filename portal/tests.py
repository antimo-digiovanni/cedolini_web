from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
from django.test import Client
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from .access import TODAY_MARKINGS_GROUP_NAME
from .models import Cud, Employee, ImportJob, Payslip, VacationRequest, WorkSession


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


class PayslipUploadImportTests(TestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._temp_media = tempfile.TemporaryDirectory()
		cls._override = override_settings(
			MEDIA_ROOT=cls._temp_media.name,
			STORAGES={
				"default": {
					"BACKEND": "django.core.files.storage.FileSystemStorage",
				},
				"staticfiles": {
					"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
				},
			},
		)
		cls._override.enable()

	@classmethod
	def tearDownClass(cls):
		cls._override.disable()
		cls._temp_media.cleanup()
		super().tearDownClass()

	def setUp(self):
		self.client = Client()
		self.admin_user = get_user_model().objects.create_user(
			username="staff.upload",
			password="Password123!",
			is_staff=True,
		)
		self.client.force_login(self.admin_user)

		self.active_user = get_user_model().objects.create_user(
			username="mario.rossi",
			password="Password123!",
			is_active=True,
		)
		self.active_employee = Employee.objects.create(
			user=self.active_user,
			first_name="Mario",
			last_name="Rossi",
		)

		self.inactive_user = get_user_model().objects.create_user(
			username="anna.bianchi",
			password="Password123!",
			is_active=False,
		)
		self.inactive_employee = Employee.objects.create(
			user=self.inactive_user,
			first_name="Anna",
			last_name="Bianchi",
		)

	def _pdf_file(self, name):
		return SimpleUploadedFile(name, b"%PDF-1.4\n%test pdf\n", content_type="application/pdf")

	def test_upload_imports_only_employees_with_active_account(self):
		response = self.client.post(
			reverse("admin_upload_period_folder"),
			{
				"folder": [
					self._pdf_file("Rossi Mario Gennaio 2026.pdf"),
					self._pdf_file("Bianchi Anna Gennaio 2026.pdf"),
					self._pdf_file("Verdi Luca Gennaio 2026.pdf"),
				]
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Conferma Account Mancanti")

		confirm_response = self.client.post(
			reverse("admin_upload_period_folder"),
			{
				"action": "resolve_pending_import",
			},
		)

		self.assertEqual(confirm_response.status_code, 200)
		self.assertEqual(Payslip.objects.filter(employee=self.active_employee, year=2026, month=1).count(), 1)
		self.assertEqual(Payslip.objects.filter(employee=self.inactive_employee, year=2026, month=1).count(), 0)
		self.assertEqual(Payslip.objects.count(), 1)
		self.assertEqual(Employee.objects.count(), 2)

		job = ImportJob.objects.latest("created_at")
		self.assertEqual(job.created_users, 0)
		self.assertEqual(job.created_payslips, 1)
		self.assertEqual(job.skipped, 2)
		self.assertEqual(job.status, "completed")

		self.assertContains(confirm_response, "account non attivo")
		self.assertContains(confirm_response, "account non creato")

	def test_upload_can_create_missing_employee_and_save_payslip(self):
		response = self.client.post(
			reverse("admin_upload_period_folder"),
			{
				"folder": [self._pdf_file("Verdi Luca Gennaio 2026.pdf")]
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Conferma Account Mancanti")

		confirm_response = self.client.post(
			reverse("admin_upload_period_folder"),
			{
				"action": "resolve_pending_import",
				"create_candidates": ["verdi-luca"],
				"first_name_verdi-luca": "Luca",
				"last_name_verdi-luca": "Verdi",
			},
		)

		self.assertEqual(confirm_response.status_code, 200)
		created_employee = Employee.objects.get(last_name="Verdi", first_name="Luca")
		self.assertFalse(created_employee.user.is_active)
		self.assertEqual(Payslip.objects.filter(employee=created_employee, year=2026, month=1).count(), 1)
		self.assertContains(confirm_response, "Account creati: 1")

	def test_upload_prefers_existing_active_registered_employee_when_duplicate_name_exists(self):
		duplicate_user = get_user_model().objects.create_user(
			username="mario.rossi.duplicate",
			password="Password123!",
			is_active=False,
		)
		duplicate_employee = Employee.objects.create(
			user=duplicate_user,
			first_name="Mario",
			last_name="Rossi",
		)

		self.active_employee.privacy_accepted = True
		self.active_employee.save(update_fields=["privacy_accepted"])

		response = self.client.post(
			reverse("admin_upload_period_folder"),
			{
				"folder": [self._pdf_file("Mario Rossi Gennaio 2026.pdf")]
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Payslip.objects.filter(employee=self.active_employee, year=2026, month=1).count(), 1)
		self.assertEqual(Payslip.objects.filter(employee=duplicate_employee, year=2026, month=1).count(), 0)

	def test_upload_matches_employee_from_username_when_names_are_missing(self):
		username_user = get_user_model().objects.create_user(
			username="daponte-giuseppe",
			password="Password123!",
			is_active=True,
		)
		username_employee = Employee.objects.create(
			user=username_user,
			first_name="",
			last_name="",
		)

		response = self.client.post(
			reverse("admin_upload_period_folder"),
			{
				"folder": [self._pdf_file("D'Aponte Giuseppe Gennaio 2026.pdf")]
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Payslip.objects.filter(employee=username_employee, year=2026, month=1).count(), 1)


class CudUploadImportTests(TestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._temp_media = tempfile.TemporaryDirectory()
		cls._override = override_settings(
			MEDIA_ROOT=cls._temp_media.name,
			STORAGES={
				"default": {
					"BACKEND": "django.core.files.storage.FileSystemStorage",
				},
				"staticfiles": {
					"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
				},
			},
		)
		cls._override.enable()

	@classmethod
	def tearDownClass(cls):
		cls._override.disable()
		cls._temp_media.cleanup()
		super().tearDownClass()

	def setUp(self):
		self.client = Client()
		self.admin_user = get_user_model().objects.create_user(
			username="staff.cud",
			password="Password123!",
			is_staff=True,
		)
		self.client.force_login(self.admin_user)

		self.active_user = get_user_model().objects.create_user(
			username="mario.rossi",
			password="Password123!",
			is_active=True,
		)
		self.active_employee = Employee.objects.create(
			user=self.active_user,
			first_name="Mario",
			last_name="Rossi",
		)

		self.inactive_user = get_user_model().objects.create_user(
			username="anna.bianchi",
			password="Password123!",
			is_active=False,
		)
		self.inactive_employee = Employee.objects.create(
			user=self.inactive_user,
			first_name="Anna",
			last_name="Bianchi",
		)

	def _pdf_file(self, name, content=b"%PDF-1.4\n%test pdf\n"):
		return SimpleUploadedFile(name, content, content_type="application/pdf")

	def test_upload_imports_only_cuds_for_active_accounts(self):
		response = self.client.post(
			reverse("admin_upload_cud"),
			{
				"files": [
					self._pdf_file("CU2026_ROSSI_MARIO.pdf"),
					self._pdf_file("CU2026_BIANCHI_ANNA.pdf"),
					self._pdf_file("CU2026_VERDI_LUCA.pdf"),
				]
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Conferma Account Mancanti")

		confirm_response = self.client.post(
			reverse("admin_upload_cud"),
			{
				"action": "resolve_pending_import",
			},
		)

		self.assertEqual(confirm_response.status_code, 200)
		self.assertEqual(Cud.objects.filter(employee=self.active_employee, year=2026).count(), 1)
		self.assertEqual(Cud.objects.filter(employee=self.inactive_employee, year=2026).count(), 0)
		self.assertEqual(Cud.objects.count(), 1)
		self.assertContains(confirm_response, "account non attivo")
		self.assertContains(confirm_response, "account non creato")

	def test_upload_can_create_missing_employee_and_save_cud(self):
		response = self.client.post(
			reverse("admin_upload_cud"),
			{
				"files": [self._pdf_file("CU2026_VERDI_LUCA.pdf")]
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Conferma Account Mancanti")

		confirm_response = self.client.post(
			reverse("admin_upload_cud"),
			{
				"action": "resolve_pending_import",
				"create_candidates": ["verdi-luca"],
				"first_name_verdi-luca": "Luca",
				"last_name_verdi-luca": "Verdi",
			},
		)

		self.assertEqual(confirm_response.status_code, 200)
		created_employee = Employee.objects.get(last_name="Verdi", first_name="Luca")
		self.assertFalse(created_employee.user.is_active)
		self.assertEqual(Cud.objects.filter(employee=created_employee, year=2026).count(), 1)
		self.assertContains(confirm_response, "Account creati: 1")

	def test_upload_matches_employee_from_username_when_names_are_missing(self):
		username_user = get_user_model().objects.create_user(
			username="daponte-giuseppe",
			password="Password123!",
			is_active=True,
		)
		username_employee = Employee.objects.create(
			user=username_user,
			first_name="",
			last_name="",
		)

		response = self.client.post(
			reverse("admin_upload_cud"),
			{
				"files": [self._pdf_file("CU2026_D'APONTE_GIUSEPPE.pdf")]
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Cud.objects.filter(employee=username_employee, year=2026).count(), 1)

	def test_upload_replaces_existing_cud_for_same_employee_and_year(self):
		existing = Cud.objects.create(
			employee=self.active_employee,
			year=2026,
			pdf=self._pdf_file("old.pdf", content=b"%PDF-1.4\n%old\n"),
		)

		response = self.client.post(
			reverse("admin_upload_cud"),
			{
				"files": [self._pdf_file("CU2026_ROSSI_MARIO.pdf", content=b"%PDF-1.4\n%new\n")]
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Cud.objects.filter(employee=self.active_employee, year=2026).count(), 1)
		self.assertFalse(Cud.objects.filter(id=existing.id).exists())
		self.assertContains(response, "Sostituiti: 1")
