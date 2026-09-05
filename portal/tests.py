from io import BytesIO
from pathlib import Path
from decimal import Decimal
from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
from django.test import Client
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import datetime
from PIL import Image

from .access import TODAY_MARKINGS_GROUP_NAME, TURNI_PLANNER_GROUP_NAME, PATRIMONIO_GROUP_NAME
from .models import Cud, CorporateCardEntry, Employee, EmployeeWorkZone, ImportJob, Payslip, PersonalAssetEntry, PlannedCorporateCardExpense, PortalUserSetting, TurniPlannerWeekState, VacationRequest, WorkSession, WorkZone


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
		self.turni_state = TurniPlannerWeekState.objects.create(
			week_label="WEEK OWNER",
			visible_to_employees=True,
			planner_data={
				"weekly": {
					"headers": ["Reparto A", "Reparto B", "Reparto C", "", "", "", "", "", "", ""],
					"central_departments": [""] * 10,
					"sections": [
						{"label": "1 turno", "time_values": ["06:00", "06:00", "06:00", "", "", "", "", "", "", ""], "rows": [["Mario", "Luca", "Anna", "", "", "", "", "", "", ""], [""] * 10, [""] * 10]},
						{"label": "2 turno", "time_values": [""] * 10, "rows": [[""] * 10, [""] * 10, [""] * 10]},
						{"label": "3 turno", "time_values": [""] * 10, "rows": [[""] * 10, [""] * 10, [""] * 10]},
						{"label": "turno centrale", "time_values": [""] * 10, "rows": [[""] * 10, [""] * 10, [""] * 10]},
					],
				},
				"saturday": {"base_date": "24/05/2026", "rows": [["24/05/2026", "Mattina", "Mario", "Capo A", "Presidio", "Reparto A"]]},
				"sunday": {"base_date": "25/05/2026", "rows": [["25/05/2026", "Sera", "Luca", "Capo B", "Supporto", "Reparto B"]]},
				"scorrimento": {"title": "Scorrimento demo", "base_date": "08/05/2026", "rows": [["08/05/2026", "Mattina", "Mario Rossi", "Capo A", "Scorrimento", "Reparto A"]]},
				"portineria_weekly": {
					"headers": ["PORTINERIA CENTRALE", "CENTRALINISTA", "PORTINERIA CELLA"],
					"sections": [
						{"label": "1 turno", "time_values": ["06:14", "08:17", "06:14"], "rows": [["A", "B", "C"], ["", "", ""], ["", "", ""]]},
						{"label": "2 turno", "time_values": ["14:22", "", "14:22"], "rows": [["", "", ""], ["", "", ""], ["", "", ""]]},
						{"label": "3 turno", "time_values": ["22:06", "", "22:06"], "rows": [["", "", ""], ["", "", ""], ["", "", ""]]},
					],
				},
				"portineria_weekend": {"base_date": "24/05/2026", "rows": [["24/05/2026", "Mattina", "Port A", "Resp A", "Controllo", "Portineria"]]},
			},
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

	def test_employee_with_today_markings_group_keeps_employee_home(self):
		self.employee_user.groups.add(self.group)
		self.client.force_login(self.employee_user)
		response = self.client.get(reverse("home"))
		self.assertRedirects(response, reverse("dashboard"))

	def test_employee_with_today_markings_group_keeps_timekeeping_page(self):
		self.employee_user.groups.add(self.group)
		self.client.force_login(self.employee_user)
		response = self.client.get(reverse("timekeeping"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Marcatura")

	def test_employee_with_today_markings_group_can_still_open_today_markings_page(self):
		self.employee_user.groups.add(self.group)
		self.client.force_login(self.employee_user)
		response = self.client.get(reverse("today_markings_dashboard"))
		self.assertEqual(response.status_code, 200)


	def test_employee_with_today_markings_group_sees_markings_open_in_dashboard(self):
		self.employee_user.groups.add(self.group)
		self.client.force_login(self.employee_user)
		response = self.client.get(reverse("dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Chi ha marcato oggi")
		self.assertContains(response, "Ingresso")
		self.assertContains(response, "Luca Verdi")

	def test_limited_user_can_view_today_markings_page(self):
		self.client.force_login(self.owner_user)
		response = self.client.get(reverse("today_markings_dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Chi ha marcato oggi")
		self.assertContains(response, "Luca Verdi")

	def test_limited_user_does_not_see_mark_coordinates(self):
		session = WorkSession.objects.filter(employee=self.employee, work_date=timezone.localdate()).first()
		session.start_latitude = "40.123456"
		session.start_longitude = "14.654321"
		session.save(update_fields=["start_latitude", "start_longitude"])

		self.client.force_login(self.owner_user)
		response = self.client.get(reverse("today_markings_dashboard"))

		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, "Coordinate ingresso")
		self.assertNotContains(response, "40.123456, 14.654321")

	def test_limited_user_sees_published_turni_on_today_markings_by_default(self):
		self.client.force_login(self.owner_user)
		response = self.client.get(reverse("today_markings_dashboard"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Turni della settimana")
		self.assertContains(response, self.turni_state.week_label)
		self.assertContains(response, reverse("employee_turni_published_image", args=["weekly"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["portineria_weekly"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["scorrimento"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["portineria_weekend"]))
		self.assertContains(response, "Scorrimento")
		self.assertContains(response, "Portineria settimana")
		self.assertContains(response, "Portineria weekend")

		image_response = self.client.get(reverse("employee_turni_published_image", args=["weekly"]))
		self.assertEqual(image_response.status_code, 200)
		portineria_response = self.client.get(reverse("employee_turni_published_image", args=["portineria_weekly"]))
		self.assertEqual(portineria_response.status_code, 200)

	def test_limited_user_sees_only_selected_published_turni_sections(self):
		self.turni_state.planner_data["published_sections"] = ["weekly", "saturday", "sunday"]
		self.turni_state.save(update_fields=["planner_data"])
		self.client.force_login(self.owner_user)

		response = self.client.get(reverse("today_markings_dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, reverse("employee_turni_published_image", args=["weekly"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["saturday"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["sunday"]))
		self.assertNotContains(response, reverse("employee_turni_published_image", args=["portineria_weekly"]))
		self.assertNotContains(response, reverse("employee_turni_published_image", args=["portineria_weekend"]))

		portineria_response = self.client.get(reverse("employee_turni_published_image", args=["portineria_weekly"]))
		self.assertEqual(portineria_response.status_code, 404)

	def test_limited_user_can_be_disabled_from_published_turni(self):
		PortalUserSetting.objects.update_or_create(
			user=self.owner_user,
			defaults={"show_published_turni": False},
		)
		self.client.force_login(self.owner_user)

		response = self.client.get(reverse("today_markings_dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, "Turni della settimana")

		image_response = self.client.get(reverse("employee_turni_published_image", args=["weekly"]))
		self.assertEqual(image_response.status_code, 404)

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

	def test_today_markings_includes_overnight_exit_on_next_day(self):
		WorkSession.objects.all().delete()
		yesterday = timezone.localdate() - timezone.timedelta(days=1)
		today = timezone.localdate()
		tz = timezone.get_current_timezone()
		started_at = timezone.make_aware(datetime.combine(yesterday, datetime.strptime("17:00", "%H:%M").time()), tz)
		ended_at = timezone.make_aware(datetime.combine(today, datetime.strptime("01:00", "%H:%M").time()), tz)
		WorkSession.objects.create(
			employee=self.employee,
			work_date=yesterday,
			started_at=started_at,
			ended_at=ended_at,
		)

		self.client.force_login(self.owner_user)
		response_today = self.client.get(reverse("today_markings_dashboard"))
		self.assertEqual(response_today.status_code, 200)
		self.assertContains(response_today, "Luca Verdi")
		self.assertContains(response_today, "01:00")
		self.assertContains(response_today, "--:--")

		response_yesterday = self.client.get(reverse("today_markings_dashboard"), {"date": yesterday.isoformat()})
		self.assertEqual(response_yesterday.status_code, 200)
		self.assertContains(response_yesterday, "Luca Verdi")
		self.assertContains(response_yesterday, "17:00")


class PersonalAssetDashboardTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.group = Group.objects.create(name=PATRIMONIO_GROUP_NAME)
		self.user = get_user_model().objects.create_user(
			username="patrimonio.user",
			password="Password123!",
			first_name="Patrimonio",
			last_name="User",
		)
		self.employee = Employee.objects.create(
			user=self.user,
			first_name="Patrimonio",
			last_name="User",
		)
		self.user.groups.add(self.group)

	def test_dashboard_requires_group_access(self):
		other_user = get_user_model().objects.create_user(username="no.patrimonio", password="Password123!")
		self.client.force_login(other_user)
		response = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(response.status_code, 403)

	def test_creates_entry_and_updates_balances(self):
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_entry",
			"occurred_on": timezone.localdate().isoformat(),
			"operation_type": PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE,
			"category": "Trasferta",
			"amount": "50.00",
			"reimbursement_amount": "40.00",
			"description": "Pranzo e benzina",
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=created")
		entry = PersonalAssetEntry.objects.get(user=self.user)
		self.assertEqual(entry.account_delta, Decimal("-50.00"))
		self.assertEqual(entry.reimbursement_delta, Decimal("40.00"))

		page = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(page.status_code, 200)
		self.assertEqual(page.context["finance_summary"]["total_assets"], Decimal("-10.00"))
		self.assertEqual(page.context["finance_summary"]["reimbursement_balance"], Decimal("40.00"))

	def test_can_hide_reimbursements_from_total_assets(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE_PENDING,
			category="Trasferta",
			amount=Decimal("120.00"),
			reimbursement_amount=Decimal("120.00"),
			description="Spesa futura",
		)
		self.client.force_login(self.user)
		response = self.client.get(reverse("personal_asset_dashboard"), {"show_reimbursement_in_assets": "0"})
		self.assertEqual(response.context["finance_summary"]["reimbursement_balance"], Decimal("120.00"))
		self.assertEqual(response.context["finance_summary"]["total_assets"], Decimal("0.00"))
		self.assertFalse(response.context["show_reimbursement_in_assets"])

	def test_creates_pending_reimbursable_expense_without_reducing_account(self):
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_entry",
			"occurred_on": timezone.localdate().isoformat(),
			"operation_type": PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE_PENDING,
			"category": "Trasferta",
			"amount": "120.00",
			"reimbursement_amount": "120.00",
			"description": "Spesa che pago solo dopo il rimborso",
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=created")
		entry = PersonalAssetEntry.objects.get(user=self.user)
		self.assertEqual(entry.account_delta, Decimal("0.00"))
		self.assertEqual(entry.reimbursement_delta, Decimal("120.00"))

		page = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(page.context["finance_summary"]["account_balance"], Decimal("0.00"))
		self.assertEqual(page.context["finance_summary"]["reimbursement_balance"], Decimal("120.00"))
		self.assertEqual(page.context["reimbursement_report_entries_count"], 1)

	def test_can_reset_reimbursement_balance_to_zero(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSEMENT_RECEIVED,
			category="Rimborso spese",
			amount=Decimal("530.01"),
			description="Rimborso registrato in eccesso",
		)
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "reset_reimbursement_balance",
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=reimbursement_adjusted")

		page = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(page.context["finance_summary"]["reimbursement_balance"], Decimal("0.00"))
		self.assertEqual(page.context["finance_summary"]["reimbursement_adjustment"], Decimal("530.01"))

	def test_corporate_card_top_up_and_expense_update_card_balance(self):
		self.client.force_login(self.user)
		top_up_response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_corporate_card_entry",
			"occurred_on": "2026-08-01",
			"operation_type": CorporateCardEntry.TYPE_TOP_UP,
			"category": "Ricarica datore",
			"amount": "500.00",
			"description": "Saldo iniziale agosto",
		})
		self.assertRedirects(top_up_response, reverse("personal_asset_dashboard") + "?status=corporate_card_created")

		expense_response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_corporate_card_entry",
			"occurred_on": "2026-08-03",
			"operation_type": CorporateCardEntry.TYPE_EXPENSE,
			"category": "Carburante",
			"amount": "125.50",
			"description": "Trasferta",
		})
		self.assertRedirects(expense_response, reverse("personal_asset_dashboard") + "?status=corporate_card_created")

		page = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(page.context["corporate_card_balance"], Decimal("374.50"))
		self.assertEqual(page.context["corporate_card_month"]["top_up_total"], Decimal("500.00"))
		self.assertEqual(page.context["corporate_card_month"]["expense_total"], Decimal("125.50"))

		report = self.client.get(reverse("personal_asset_dashboard"), {
			"report": "corporate_card",
			"year": "2026",
			"month": "8",
		})
		self.assertEqual(report.status_code, 200)
		self.assertEqual(report.context["report_net_total"], Decimal("374.50"))
		self.assertContains(report, "Gestione carta di credito aziendale")

	def test_corporate_card_top_up_requires_only_amount(self):
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_corporate_card_entry",
			"operation_type": CorporateCardEntry.TYPE_TOP_UP,
			"amount": "300.00",
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=corporate_card_created")
		entry = CorporateCardEntry.objects.get(user=self.user)
		self.assertEqual(entry.amount, Decimal("300.00"))
		self.assertEqual(entry.category, "Ricarica datore")
		self.assertEqual(entry.occurred_on, timezone.localdate())

	def test_corporate_card_rejects_expense_above_available_balance(self):
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_corporate_card_entry",
			"occurred_on": "2026-08-03",
			"operation_type": CorporateCardEntry.TYPE_EXPENSE,
			"category": "Materiale",
			"amount": "1.00",
		})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(CorporateCardEntry.objects.filter(user=self.user).count(), 0)
		self.assertContains(response, "La spesa supera il saldo disponibile")

	def test_planned_expenses_are_printable_and_move_to_card_when_paid(self):
		self.client.force_login(self.user)
		for category, amount in (("Materiale", "40.00"), ("Carburante", "60.00")):
			response = self.client.post(reverse("personal_asset_dashboard"), {
				"action": "create_planned_corporate_card_expense",
				"planned_on": "2026-08-21",
				"category": category,
				"amount": amount,
				"description": f"Spesa {category}",
			})
			self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=planned_expense_created")

		planned_ids = list(PlannedCorporateCardExpense.objects.values_list('id', flat=True))
		pdf_response = self.client.get(reverse("personal_asset_dashboard"), {"report": "planned_corporate_card_pdf"})
		self.assertEqual(pdf_response.status_code, 200)
		self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
		self.assertIn(b'%PDF', pdf_response.content[:20])

		self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_corporate_card_entry",
			"operation_type": CorporateCardEntry.TYPE_TOP_UP,
			"amount": "100.00",
		})
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "mark_planned_expenses_paid",
			"planned_expense_ids": [str(item_id) for item_id in planned_ids],
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=planned_expenses_paid")
		self.assertEqual(PlannedCorporateCardExpense.objects.filter(paid_entry__isnull=True).count(), 0)
		self.assertEqual(CorporateCardEntry.objects.filter(operation_type=CorporateCardEntry.TYPE_EXPENSE).count(), 2)
		self.assertEqual(CorporateCardEntry.objects.filter(user=self.user).count(), 3)

	@override_settings(STORAGES={
		'default': {
			'BACKEND': 'django.core.files.storage.FileSystemStorage',
			'OPTIONS': {'location': tempfile.gettempdir()},
		},
		'staticfiles': {
			'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
		},
	})
	def test_planned_expenses_pdf_includes_receipt_attachment(self):
		image_buffer = BytesIO()
		Image.new('RGB', (40, 60), color='white').save(image_buffer, format='PNG')
		image_buffer.seek(0)
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_planned_corporate_card_expense",
			"planned_on": "2026-08-21",
			"category": "Scontrino allegato",
			"amount": "35.00",
			"receipt_image": SimpleUploadedFile('scontrino-previsto.png', image_buffer.getvalue(), content_type='image/png'),
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=planned_expense_created")

		pdf_response = self.client.get(reverse("personal_asset_dashboard"), {"report": "planned_corporate_card_pdf"})
		self.assertEqual(pdf_response.status_code, 200)
		self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
		self.assertIn(b'%PDF', pdf_response.content[:20])
		self.assertTrue(PlannedCorporateCardExpense.objects.get(category="Scontrino allegato").receipt_image.name)

	@override_settings(STORAGES={
		'default': {
			'BACKEND': 'django.core.files.storage.FileSystemStorage',
			'OPTIONS': {'location': tempfile.gettempdir()},
		},
		'staticfiles': {
			'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
		},
	})
	def test_corporate_card_pdf_includes_receipt_attachment(self):
		image_buffer = BytesIO()
		Image.new('RGB', (40, 60), color='white').save(image_buffer, format='PNG')
		image_buffer.seek(0)
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_corporate_card_entry",
			"occurred_on": "2026-08-20",
			"operation_type": CorporateCardEntry.TYPE_TOP_UP,
			"amount": "500.00",
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=corporate_card_created")

		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_corporate_card_entry",
			"occurred_on": "2026-08-20",
			"operation_type": CorporateCardEntry.TYPE_EXPENSE,
			"amount": "25.00",
			"category": "Pranzo",
			"description": "Scontrino pranzo",
			"receipt_image": SimpleUploadedFile('scontrino.png', image_buffer.getvalue(), content_type='image/png'),
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=corporate_card_created")

		pdf_response = self.client.get(reverse("personal_asset_dashboard"), {
			"report": "corporate_card_pdf",
			"year": "2026",
			"month": "8",
		})
		self.assertEqual(pdf_response.status_code, 200)
		self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
		self.assertIn(b'%PDF', pdf_response.content[:20])
		self.assertTrue(CorporateCardEntry.objects.get(category="Pranzo").receipt_image.name)

	@override_settings(STORAGES={
		'default': {
			'BACKEND': 'django.core.files.storage.FileSystemStorage',
			'OPTIONS': {'location': tempfile.gettempdir()},
		},
		'staticfiles': {
			'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
		},
	})
	def test_corporate_card_pdf_accepts_pdf_receipt_attachment(self):
		from reportlab.pdfgen import canvas

		pdf_buffer = BytesIO()
		pdf_canvas = canvas.Canvas(pdf_buffer)
		pdf_canvas.drawString(40, 760, 'Documento scontrino PDF')
		pdf_canvas.save()
		pdf_buffer.seek(0)
		self.client.force_login(self.user)
		self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_corporate_card_entry",
			"operation_type": CorporateCardEntry.TYPE_TOP_UP,
			"amount": "100.00",
		})
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_corporate_card_entry",
			"operation_type": CorporateCardEntry.TYPE_EXPENSE,
			"amount": "20.00",
			"category": "Documento",
			"receipt_image": SimpleUploadedFile('documento.pdf', pdf_buffer.getvalue(), content_type='application/pdf'),
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=corporate_card_created")
		pdf_response = self.client.get(reverse("personal_asset_dashboard"), {
			"report": "corporate_card_pdf",
			"year": "2026",
			"month": "8",
		})
		self.assertEqual(pdf_response.status_code, 200)
		self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
		self.assertTrue(CorporateCardEntry.objects.get(category="Documento").receipt_image.name.endswith('.pdf'))

	def test_reimbursement_report_entries_are_sorted_by_oldest_date_first(self):
		from .views import _build_personal_asset_reimbursement_report_image

		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 12).date(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE,
			category="Trasferta",
			amount=Decimal("30.00"),
			reimbursement_amount=Decimal("30.00"),
			description="Terza",
		)
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 10).date(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE_PENDING,
			category="Trasferta",
			amount=Decimal("10.00"),
			reimbursement_amount=Decimal("10.00"),
			description="Prima",
		)
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 11).date(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE,
			category="Trasferta",
			amount=Decimal("20.00"),
			reimbursement_amount=Decimal("20.00"),
			description="Seconda",
		)

		_, reimbursement_entries, _ = _build_personal_asset_reimbursement_report_image(self.user)
		self.assertEqual([entry.description for entry in reimbursement_entries], ["Prima", "Seconda", "Terza"])

	def test_can_reset_only_open_reimbursement_report_entries(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE_PENDING,
			category="Trasferta",
			amount=Decimal("120.00"),
			reimbursement_amount=Decimal("120.00"),
			description="Spesa aperta",
		)
		settlement = PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSEMENT_RECEIVED,
			category="Rimborso spese",
			amount=Decimal("50.00"),
			description="Liquidazione precedente",
		)
		archived_entry = PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE,
			category="Hotel",
			amount=Decimal("50.00"),
			reimbursement_amount=Decimal("50.00"),
			description="Spesa archiviata",
			reimbursement_settlement=settlement,
		)

		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "reset_reimbursement_entries",
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=reimbursement_reset")
		self.assertFalse(PersonalAssetEntry.objects.filter(description="Spesa aperta").exists())
		self.assertTrue(PersonalAssetEntry.objects.filter(id=archived_entry.id).exists())

		page = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(page.context["reimbursement_report_entries_count"], 0)
		self.assertEqual(page.context["archived_reimbursement_groups"][0]["entry_count"], 1)

	def test_quick_adjusts_account_balance_without_creating_entry(self):
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "adjust_account_balance",
			"direction": "increase",
			"amount": "75.00",
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=account_adjusted")
		self.assertEqual(PersonalAssetEntry.objects.filter(user=self.user).count(), 0)
		self.user.refresh_from_db()
		self.assertEqual(self.user.portal_setting.personal_asset_account_adjustment, Decimal("75.00"))

		page = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(page.context["finance_summary"]["account_balance"], Decimal("75.00"))
		self.assertEqual(page.context["finance_summary"]["account_adjustment"], Decimal("75.00"))

	def test_quick_decreases_account_balance_without_creating_entry(self):
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "adjust_account_balance",
			"direction": "decrease",
			"amount": "20.00",
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=account_adjusted")
		self.assertEqual(PersonalAssetEntry.objects.filter(user=self.user).count(), 0)

		page = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(page.context["finance_summary"]["account_balance"], Decimal("-20.00"))
		self.assertEqual(page.context["finance_summary"]["account_adjustment"], Decimal("-20.00"))

	def test_can_set_exact_account_balance_without_creating_entry(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_INCOME,
			category="Stipendio",
			amount=Decimal("10.00"),
		)
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "set_account_balance",
			"amount": "250.00",
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=account_adjusted")
		self.user.refresh_from_db()
		self.assertEqual(self.user.portal_setting.personal_asset_account_adjustment, Decimal("240.00"))

		page = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(page.context["finance_summary"]["account_balance"], Decimal("250.00"))

	def test_credit_card_personal_expense_is_pending_until_next_month_charge(self):
		from .views import _personal_asset_summary

		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 20).date(),
			operation_type=PersonalAssetEntry.TYPE_CREDIT_CARD_EXPENSE,
			category="Carta di credito",
			amount=Decimal("100.00"),
			description="Acquisto personale",
		)

		july_summary = _personal_asset_summary(self.user, reference_date=datetime(2026, 7, 31).date())
		self.assertEqual(july_summary["account_balance"], Decimal("0.00"))
		self.assertEqual(july_summary["pending_credit_card_balance"], Decimal("100.00"))
		self.assertEqual(july_summary["total_assets"], Decimal("-100.00"))
		self.assertEqual(july_summary["monthly_expense"], Decimal("100.00"))
		self.assertEqual(july_summary["monthly_saving"], Decimal("-100.00"))
		self.assertEqual(july_summary["monthly_cash_flow"], Decimal("0.00"))

		august_summary = _personal_asset_summary(self.user, reference_date=datetime(2026, 8, 15).date())
		self.assertEqual(august_summary["account_balance"], Decimal("-100.00"))
		self.assertEqual(august_summary["pending_credit_card_balance"], Decimal("0.00"))
		self.assertEqual(august_summary["monthly_cash_flow"], Decimal("-100.00"))

	def test_credit_card_reimbursable_expense_tracks_reimbursement_and_charge(self):
		from .views import _personal_asset_monthly_summaries, _personal_asset_summary

		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 20).date(),
			operation_type=PersonalAssetEntry.TYPE_CREDIT_CARD_REIMBURSABLE_EXPENSE,
			category="Trasferta",
			amount=Decimal("80.00"),
			reimbursement_amount=Decimal("80.00"),
			description="Taxi e pranzo",
		)

		july_summary = _personal_asset_summary(self.user, reference_date=datetime(2026, 7, 31).date())
		self.assertEqual(july_summary["account_balance"], Decimal("0.00"))
		self.assertEqual(july_summary["reimbursement_balance"], Decimal("80.00"))
		self.assertEqual(july_summary["pending_credit_card_balance"], Decimal("80.00"))
		self.assertEqual(july_summary["projected_account_balance"], Decimal("0.00"))

		august_12_summary = _personal_asset_summary(self.user, reference_date=datetime(2026, 8, 12).date())
		self.assertEqual(august_12_summary["account_balance"], Decimal("80.00"))
		self.assertEqual(august_12_summary["reimbursement_balance"], Decimal("0.00"))
		self.assertEqual(august_12_summary["pending_credit_card_balance"], Decimal("80.00"))

		august_16_summary = _personal_asset_summary(self.user, reference_date=datetime(2026, 8, 16).date())
		self.assertEqual(august_16_summary["account_balance"], Decimal("0.00"))
		self.assertEqual(august_16_summary["reimbursement_balance"], Decimal("0.00"))
		self.assertEqual(august_16_summary["pending_credit_card_balance"], Decimal("0.00"))

		monthly_summaries = _personal_asset_monthly_summaries(self.user)
		self.assertEqual(monthly_summaries[0]["label"], "Agosto 2026")
		self.assertEqual(monthly_summaries[0]["income"], Decimal("80.00"))
		self.assertEqual(monthly_summaries[0]["expense"], Decimal("0.00"))
		self.assertEqual(monthly_summaries[0]["cash_flow"], Decimal("0.00"))
		self.assertEqual(monthly_summaries[1]["label"], "Luglio 2026")
		self.assertEqual(monthly_summaries[1]["expense"], Decimal("80.00"))

	def test_creates_reimbursement_paid_and_salary_income(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE,
			category="Trasferta",
			amount=Decimal("50.00"),
			reimbursement_amount=Decimal("40.00"),
			description="Pranzo e benzina",
		)
		self.client.force_login(self.user)
		reimbursement_response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_entry",
			"occurred_on": timezone.localdate().isoformat(),
			"operation_type": PersonalAssetEntry.TYPE_REIMBURSEMENT_RECEIVED,
			"category": "Rimborso spese",
			"amount": "40.00",
			"description": "Rimborso pagato",
		})
		self.assertRedirects(reimbursement_response, reverse("personal_asset_dashboard") + "?status=created")
		salary_response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "create_entry",
			"occurred_on": timezone.localdate().isoformat(),
			"operation_type": PersonalAssetEntry.TYPE_INCOME,
			"category": "Stipendio",
			"amount": "1500.00",
			"description": "Entrata stipendio",
		})
		self.assertRedirects(salary_response, reverse("personal_asset_dashboard") + "?status=created")

		page = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(page.context["finance_summary"]["account_balance"], Decimal("1490.00"))
		self.assertEqual(page.context["finance_summary"]["reimbursement_balance"], Decimal("0.00"))
		self.assertEqual(page.context["finance_summary"]["total_assets"], Decimal("1490.00"))
		self.assertEqual(page.context["reimbursement_report_entries_count"], 0)
		self.assertEqual(page.context["reimbursement_report_total"], Decimal("0.00"))

		reimbursement_paid_entry = PersonalAssetEntry.objects.get(
			user=self.user,
			operation_type=PersonalAssetEntry.TYPE_REIMBURSEMENT_RECEIVED,
		)
		archived_entry = PersonalAssetEntry.objects.get(
			user=self.user,
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE,
		)
		self.assertEqual(archived_entry.reimbursement_settlement_id, reimbursement_paid_entry.id)

	def test_deleting_reimbursement_paid_reopens_reimbursement_report_entries(self):
		open_entry = PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE_PENDING,
			category="Trasferta",
			amount=Decimal("120.00"),
			reimbursement_amount=Decimal("120.00"),
			description="Hotel",
		)
		reimbursement_paid_entry = PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSEMENT_RECEIVED,
			category="Rimborso spese",
			amount=Decimal("120.00"),
			description="Rimborso hotel",
		)
		open_entry.reimbursement_settlement = reimbursement_paid_entry
		open_entry.save(update_fields=["reimbursement_settlement"])

		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "delete_entry",
			"entry_id": str(reimbursement_paid_entry.id),
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=deleted")

		open_entry.refresh_from_db()
		self.assertIsNone(open_entry.reimbursement_settlement_id)

		page = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(page.context["reimbursement_report_entries_count"], 1)
		self.assertEqual(page.context["reimbursement_report_total"], Decimal("120.00"))

	def test_archived_reimbursements_are_grouped_by_settlement_month(self):
		july_settlement = PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 10).date(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSEMENT_RECEIVED,
			category="Rimborso spese",
			amount=Decimal("75.00"),
			description="Rimborso luglio",
		)
		july_entry = PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 5).date(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE,
			category="Trasferta",
			amount=Decimal("80.00"),
			reimbursement_amount=Decimal("75.00"),
			description="Pranzo cliente",
			reimbursement_settlement=july_settlement,
		)
		august_settlement = PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 8, 3).date(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSEMENT_RECEIVED,
			category="Rimborso spese",
			amount=Decimal("120.00"),
			description="Rimborso agosto",
		)
		august_entry = PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 28).date(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE_PENDING,
			category="Hotel",
			amount=Decimal("120.00"),
			reimbursement_amount=Decimal("120.00"),
			description="Pernottamento",
			reimbursement_settlement=august_settlement,
		)

		self.client.force_login(self.user)
		page = self.client.get(reverse("personal_asset_dashboard"))

		groups = page.context["archived_reimbursement_groups"]
		self.assertEqual(len(groups), 2)
		self.assertEqual(groups[0]["label"], "Agosto 2026")
		self.assertEqual(groups[0]["total_amount"], Decimal("120.00"))
		self.assertEqual(groups[0]["entry_count"], 1)
		self.assertEqual(groups[0]["settlements"][0]["entries"][0].id, august_entry.id)
		self.assertEqual(groups[1]["label"], "Luglio 2026")
		self.assertEqual(groups[1]["total_amount"], Decimal("75.00"))
		self.assertEqual(groups[1]["settlements"][0]["entries"][0].id, july_entry.id)

	def test_deletes_entry(self):
		entry = PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_EXPENSE,
			category="Spesa casa",
			amount=Decimal("25.00"),
			description="Pulizia",
		)
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "delete_entry",
			"entry_id": str(entry.id),
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=deleted")
		self.assertFalse(PersonalAssetEntry.objects.filter(id=entry.id).exists())

	def test_dashboard_no_longer_renders_personal_asset_category_suggestions(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_EXPENSE,
			category="Farmacia bimbo",
			amount=Decimal("15.00"),
			description="Sciroppo",
		)
		self.client.force_login(self.user)
		response = self.client.get(reverse("personal_asset_dashboard"))
		self.assertContains(response, "Gestione carta di credito aziendale")
		self.assertNotContains(response, 'data-category-value="Farmacia bimbo"')

	def test_dashboard_no_longer_renders_personal_asset_history(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 10).date(),
			operation_type=PersonalAssetEntry.TYPE_EXPENSE,
			category="Spesa casa",
			amount=Decimal("25.00"),
			description="Pulizia",
		)
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 6, 10).date(),
			operation_type=PersonalAssetEntry.TYPE_EXPENSE,
			category="Spesa auto",
			amount=Decimal("30.00"),
			description="Benzina",
		)
		self.client.force_login(self.user)
		response = self.client.get(reverse("personal_asset_dashboard"))
		self.assertContains(response, "Gestione carta di credito aziendale")
		self.assertNotContains(response, "Storico operazioni")
		self.assertNotContains(response, "Luglio 2026")
		self.assertNotContains(response, "Giugno 2026")

	def test_monthly_summaries_show_savings_for_each_month(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 10).date(),
			operation_type=PersonalAssetEntry.TYPE_INCOME,
			category="Stipendio",
			amount=Decimal("1000.00"),
			description="Luglio stipendio",
		)
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 7, 11).date(),
			operation_type=PersonalAssetEntry.TYPE_EXPENSE,
			category="Spesa casa",
			amount=Decimal("200.00"),
			description="Luglio spesa",
		)
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=datetime(2026, 6, 10).date(),
			operation_type=PersonalAssetEntry.TYPE_INCOME,
			category="Stipendio",
			amount=Decimal("900.00"),
			description="Giugno stipendio",
		)
		self.client.force_login(self.user)
		response = self.client.get(reverse("personal_asset_dashboard"))
		monthly_summaries = response.context["finance_monthly_summaries"]
		self.assertEqual(monthly_summaries[0]["label"], "Luglio 2026")
		self.assertEqual(monthly_summaries[0]["saving"], Decimal("800.00"))
		self.assertEqual(monthly_summaries[1]["label"], "Giugno 2026")
		self.assertEqual(monthly_summaries[1]["saving"], Decimal("900.00"))

	def test_monthly_saving_excludes_reimbursements(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_INCOME,
			category="Stipendio",
			amount=Decimal("2000.00"),
			description="Stipendio",
		)
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE_PENDING,
			category="Trasferta",
			amount=Decimal("500.00"),
			reimbursement_amount=Decimal("500.00"),
			description="Rimborso futuro",
		)
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_EXPENSE,
			category="Spesa casa",
			amount=Decimal("500.00"),
			description="Spesa personale",
		)
		self.client.force_login(self.user)
		response = self.client.get(reverse("personal_asset_dashboard"))
		self.assertEqual(response.context["finance_summary"]["monthly_income"], Decimal("2000.00"))
		self.assertEqual(response.context["finance_summary"]["monthly_expense"], Decimal("500.00"))
		self.assertEqual(response.context["finance_summary"]["monthly_saving"], Decimal("1500.00"))
		self.assertEqual(response.context["finance_monthly_summaries"][0]["saving"], Decimal("1500.00"))

	def test_resets_all_entries(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_EXPENSE,
			category="Spesa casa",
			amount=Decimal("25.00"),
			description="Pulizia",
		)
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_INCOME,
			category="Stipendio",
			amount=Decimal("1200.00"),
			description="Entrata stipendio",
		)
		self.client.force_login(self.user)
		response = self.client.post(reverse("personal_asset_dashboard"), {
			"action": "reset_entries",
		})
		self.assertRedirects(response, reverse("personal_asset_dashboard") + "?status=reset")
		self.assertEqual(PersonalAssetEntry.objects.filter(user=self.user).count(), 0)

	@override_settings(EXPENSE_REIMBURSEMENT_EMAILS=["datore@example.com"])
	def test_exports_reimbursement_report_jpg(self):
		PersonalAssetEntry.objects.create(
			user=self.user,
			occurred_on=timezone.localdate(),
			operation_type=PersonalAssetEntry.TYPE_REIMBURSABLE_EXPENSE,
			category="Trasferta",
			amount=Decimal("50.00"),
			reimbursement_amount=Decimal("40.00"),
			description="Pranzo e benzina",
		)
		self.client.force_login(self.user)
		response = self.client.get(reverse("personal_asset_dashboard"), {"report": "reimbursement_jpg"})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Content-Type"], "image/jpeg")
		self.assertIn("attachment;", response["Content-Disposition"].lower())
		self.assertIn("rimborso_spese_", response["Content-Disposition"].lower())
		self.assertIn(".jpg", response["Content-Disposition"].lower())
		self.assertTrue(response.content.startswith(b"\xff\xd8\xff"))

class PublicMachineryPageTests(TestCase):
	def test_public_machinery_page_shows_real_vehicle_cards(self):
		response = self.client.get(reverse("public_machinery"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Bobcat")
		self.assertContains(response, "Gruppo elettrogeno industriale")
		self.assertContains(response, "Autospurgo canal-jet su Iveco Stralis a 4 assi")
		self.assertContains(response, "Piattaforma aerea semovente a braccio articolato JLG E300")
		self.assertContains(response, "Spazzatrice stradale aspirante Dulevo D6")
		self.assertContains(response, "Trattore stradale con semirimorchio")
		self.assertContains(response, "Magazzino operativo con carrelli")
		self.assertContains(response, "Autocarro con gru retrocabina")
		self.assertContains(response, 'data-image-count="3"')
		self.assertContains(response, 'data-image-count="4"')
		self.assertGreaterEqual(response.content.decode().count('data-image-count="2"'), 5)
		self.assertContains(response, 'alt="Bobcat"')


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

	def test_admin_can_see_mark_coordinates_in_reports(self):
		work_date = timezone.localdate()
		tz = timezone.get_current_timezone()
		WorkSession.objects.create(
			employee=self.employee,
			work_date=work_date,
			started_at=timezone.make_aware(datetime.combine(work_date, datetime.strptime("08:00", "%H:%M").time()), tz),
			ended_at=timezone.make_aware(datetime.combine(work_date, datetime.strptime("17:00", "%H:%M").time()), tz),
			start_latitude="40.123456",
			start_longitude="14.654321",
			end_latitude="40.123400",
			end_longitude="14.654300",
		)

		self.client.force_login(self.admin_user)

		report_response = self.client.get(
			reverse("admin_timekeeping"),
			{
				"employee": str(self.employee.id),
				"month": work_date.month,
				"year": work_date.year,
			},
		)
		self.assertEqual(report_response.status_code, 200)
		self.assertContains(report_response, "Coordinate ingresso")
		self.assertContains(report_response, "40.123456, 14.654321")
		self.assertContains(report_response, "40.123400, 14.654300")

		today_response = self.client.get(reverse("today_markings_dashboard"))
		self.assertEqual(today_response.status_code, 200)
		self.assertContains(today_response, "Coordinate ingresso")
		self.assertContains(today_response, "40.123456, 14.654321")
		self.assertContains(today_response, "40.123400, 14.654300")

	def test_admin_views_order_employees_by_first_name_without_changing_data(self):
		first_user = get_user_model().objects.create_user(
			username="zeno.alfa",
			password="Password123!",
		)
		second_user = get_user_model().objects.create_user(
			username="anna.zulu",
			password="Password123!",
		)
		first_employee = Employee.objects.create(
			user=first_user,
			first_name="Zeno",
			last_name="Alfa",
		)
		second_employee = Employee.objects.create(
			user=second_user,
			first_name="Anna",
			last_name="Zulu",
		)
		WorkSession.objects.create(
			employee=first_employee,
			work_date=timezone.localdate(),
			started_at=timezone.now(),
		)
		WorkSession.objects.create(
			employee=second_employee,
			work_date=timezone.localdate(),
			started_at=timezone.now(),
		)

		self.client.force_login(self.admin_user)

		employees_response = self.client.get(reverse("admin_employees"))
		self.assertEqual(employees_response.status_code, 200)
		employees_html = employees_response.content.decode()
		self.assertLess(employees_html.index("Anna Zulu"), employees_html.index("Zeno Alfa"))

		timekeeping_response = self.client.get(
			reverse("admin_timekeeping"),
			{
				"employee": "all",
				"month": timezone.localdate().month,
				"year": timezone.localdate().year,
			},
		)
		self.assertEqual(timekeeping_response.status_code, 200)
		timekeeping_html = timekeeping_response.content.decode()
		self.assertLess(timekeeping_html.index("Anna Zulu"), timekeeping_html.index("Zeno Alfa"))
		self.assertEqual(Employee.objects.get(id=first_employee.id).last_name, "Alfa")
		self.assertEqual(Employee.objects.get(id=second_employee.id).last_name, "Zulu")


class TimekeepingAjaxGeolocationTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = get_user_model().objects.create_user(
			username="operaio.geo",
			password="Password123!",
		)
		self.employee = Employee.objects.create(
			user=self.user,
			first_name="Luciano",
			last_name="Minichini",
		)
		self.zone = WorkZone.objects.create(
			name="Stabilimento Magnum",
			latitude="40.983778",
			longitude="14.297982",
			radius_meters=550,
			is_active=True,
		)

	def test_non_strict_mark_without_geolocation_returns_json_success(self):
		EmployeeWorkZone.objects.create(
			employee=self.employee,
			zone=self.zone,
			is_active=True,
			strict_geofence=False,
		)
		self.client.force_login(self.user)

		response = self.client.post(
			reverse("timekeeping"),
			{"action": "start"},
			HTTP_X_REQUESTED_WITH="XMLHttpRequest",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Content-Type"], "application/json")
		self.assertJSONEqual(
			response.content,
			{
				"ok": True,
				"action": "start",
				"started_at": WorkSession.objects.get(employee=self.employee, work_date=timezone.localdate()).started_at.strftime("%H:%M"),
				"ended_at": None,
				"zone": self.zone.name,
				"within_zone": False,
				"distance_meters": None,
			},
		)

	def test_strict_mark_without_geolocation_returns_json_error(self):
		EmployeeWorkZone.objects.create(
			employee=self.employee,
			zone=self.zone,
			is_active=True,
			strict_geofence=True,
		)
		self.client.force_login(self.user)

		response = self.client.post(
			reverse("timekeeping"),
			{"action": "start"},
			HTTP_X_REQUESTED_WITH="XMLHttpRequest",
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response["Content-Type"], "application/json")
		self.assertJSONEqual(
			response.content,
			{
				"ok": False,
				"error": "Geolocalizzazione obbligatoria: attiva il GPS per marcare.",
			},
		)


class EmployeePublishedTurniDashboardTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.antimo_user = get_user_model().objects.create_user(
			username="antimo",
			password="Password123!",
			is_staff=True,
		)
		self.other_user = get_user_model().objects.create_user(
			username="mario",
			password="Password123!",
		)
		self.user = get_user_model().objects.create_user(
			username="employee.turni",
			password="Password123!",
		)
		self.employee = Employee.objects.create(
			user=self.user,
			first_name="Mario",
			last_name="Rossi",
		)
		self.state = TurniPlannerWeekState.objects.create(
			week_label="WEEK 21",
			visible_to_employees=True,
			planner_data={
				"weekly": {
					"headers": ["Reparto A", "Reparto B", "Reparto C", "", "", "", "", "", "", ""],
					"central_departments": [""] * 10,
					"sections": [
						{"label": "1 turno", "time_values": ["06:00", "06:00", "06:00", "", "", "", "", "", "", ""], "rows": [["Mario", "Luca", "Anna", "", "", "", "", "", "", ""], [""] * 10, [""] * 10]},
						{"label": "2 turno", "time_values": [""] * 10, "rows": [[""] * 10, [""] * 10, [""] * 10]},
						{"label": "3 turno", "time_values": [""] * 10, "rows": [[""] * 10, [""] * 10, [""] * 10]},
						{"label": "turno centrale", "time_values": [""] * 10, "rows": [[""] * 10, [""] * 10, [""] * 10]},
					],
				},
				"saturday": {
					"base_date": "24/05/2026",
					"rows": [["24/05/2026", "Mattina", "Mario", "Capo A", "Presidio", "Reparto A"]],
				},
				"sunday": {
					"base_date": "25/05/2026",
					"rows": [["25/05/2026", "Sera", "Luca", "Capo B", "Supporto", "Reparto B"]],
				},
				"jolly_weekend": {
					"title": "Comandata jolly demo",
					"base_date": "26/05/2026",
					"rows": [["26/05/2026", "Mattina", "Jolly A", "Capo J", "Presidio", "Reparto J"]],
				},
				"scorrimento": {
					"title": "Scorrimento demo",
					"base_date": "08/05/2026",
					"rows": [["08/05/2026", "Mattina", "Mario Rossi", "Capo A", "Scorrimento", "Reparto A"]],
				},
				"portineria_weekly": {
					"headers": ["PORTINERIA CENTRALE", "CENTRALINISTA", "PORTINERIA CELLA"],
					"sections": [
						{"label": "1 turno", "time_values": ["06:14", "08:17", "06:14"], "rows": [["A", "B", "C"], ["", "", ""], ["", "", ""]]},
						{"label": "2 turno", "time_values": ["14:22", "", "14:22"], "rows": [["", "", ""], ["", "", ""], ["", "", ""]]},
						{"label": "3 turno", "time_values": ["22:06", "", "22:06"], "rows": [["", "", ""], ["", "", ""], ["", "", ""]]},
					],
				},
				"portineria_weekend": {
					"base_date": "24/05/2026",
					"rows": [["24/05/2026", "Mattina", "Port A", "Resp A", "Controllo", "Portineria"]],
				},
			},
		)

	def test_employee_dashboard_shows_only_published_turni_images(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse("dashboard"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "<h2 class=\"mb-3\">Turni della settimana</h2>", html=True)
		self.assertContains(response, "Clicca per vedere i turni (7)")
		self.assertContains(response, self.state.week_label)
		self.assertContains(response, reverse("employee_turni_published_image", args=["weekly"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["portineria_weekly"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["saturday"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["sunday"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["jolly_weekend"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["scorrimento"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["portineria_weekend"]))
		self.assertContains(response, "Scorrimento")
		self.assertContains(response, "Portineria settimana")
		self.assertContains(response, "Portineria weekend")

		image_response = self.client.get(reverse("employee_turni_published_image", args=["weekly"]))
		self.assertEqual(image_response.status_code, 200)
		self.assertEqual(image_response["Content-Type"], "image/jpeg")
		self.assertTrue(image_response.content.startswith(b"\xff\xd8\xff"))

		portineria_response = self.client.get(reverse("employee_turni_published_image", args=["portineria_weekly"]))
		self.assertEqual(portineria_response.status_code, 200)

	def test_employee_dashboard_shows_only_selected_published_turni_images(self):
		self.state.planner_data["published_sections"] = ["weekly", "saturday", "sunday"]
		self.state.save(update_fields=["planner_data"])
		self.client.force_login(self.user)

		response = self.client.get(reverse("dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, reverse("employee_turni_published_image", args=["weekly"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["saturday"]))
		self.assertContains(response, reverse("employee_turni_published_image", args=["sunday"]))
		self.assertNotContains(response, reverse("employee_turni_published_image", args=["portineria_weekly"]))
		self.assertNotContains(response, reverse("employee_turni_published_image", args=["portineria_weekend"]))

		portineria_response = self.client.get(reverse("employee_turni_published_image", args=["portineria_weekly"]))
		self.assertEqual(portineria_response.status_code, 404)

	def test_employee_dashboard_hides_turni_when_nothing_is_published(self):
		self.state.visible_to_employees = False
		self.state.save(update_fields=["visible_to_employees"])
		self.client.force_login(self.user)

		response = self.client.get(reverse("dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, "Turni della settimana")

		image_response = self.client.get(reverse("employee_turni_published_image", args=["weekly"]))
		self.assertEqual(image_response.status_code, 404)

	def test_employee_dashboard_hides_turni_for_employee_disabled_in_admin(self):
		self.employee.show_published_turni = False
		self.employee.save(update_fields=["show_published_turni"])
		self.client.force_login(self.user)

		response = self.client.get(reverse("dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, "Turni della settimana")

		image_response = self.client.get(reverse("employee_turni_published_image", args=["weekly"]))
		self.assertEqual(image_response.status_code, 404)

	def test_staff_can_still_open_published_turni_images(self):
		self.client.force_login(self.antimo_user)

		image_response = self.client.get(reverse("employee_turni_published_image", args=["weekly"]))
		self.assertEqual(image_response.status_code, 200)
		self.assertEqual(image_response["Content-Type"], "image/jpeg")
class TurniPlannerAccessTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.group, _ = Group.objects.get_or_create(name=TURNI_PLANNER_GROUP_NAME)
		self.allowed_user = get_user_model().objects.create_user(
			username="planner.user",
			password="Password123!",
		)
		self.allowed_user.groups.add(self.group)
		self.denied_user = get_user_model().objects.create_user(
			username="basic.user",
			password="Password123!",
		)

	def test_turni_planner_allows_large_post_payloads(self):
		self.assertGreaterEqual(settings.DATA_UPLOAD_MAX_NUMBER_FIELDS, 20000)

	def test_home_redirects_turni_planner_user_to_planner(self):
		self.client.force_login(self.allowed_user)
		response = self.client.get(reverse("home"))
		self.assertRedirects(response, reverse("turni_planner_home"))

	def test_turni_planner_denies_non_authorized_user(self):
		self.client.force_login(self.denied_user)
		response = self.client.get(reverse("turni_planner_home"))
		self.assertEqual(response.status_code, 403)

	def test_turni_planner_disables_cache_headers(self):
		self.client.force_login(self.allowed_user)
		response = self.client.get(reverse("turni_planner_home"))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")
		self.assertEqual(response["Pragma"], "no-cache")
		self.assertEqual(response["Expires"], "0")

	def test_turni_planner_allows_group_user_and_creates_shared_week(self):
		self.client.force_login(self.allowed_user)
		response = self.client.post(
			reverse("turni_planner_home"),
			{"action": "open_week", "week_label": "Week 28 da Lunedi 06/07/2026 a Sabato 11/07/2026"},
		)

		state = TurniPlannerWeekState.objects.get()
		self.assertRedirects(response, f"{reverse('turni_planner_home')}?week={state.week_label}")
		self.assertEqual(state.updated_by, self.allowed_user)

	def test_turni_planner_deletes_requested_week(self):
		state = TurniPlannerWeekState.objects.create(
			week_label="Week 28 da Lunedi 06/07/2026 a Sabato 11/07/2026",
			planner_data={"weekly": {"headers": ["A"]}},
		)
		TurniPlannerWeekState.objects.create(
			week_label="Week 29 da Lunedi 13/07/2026 a Sabato 18/07/2026",
			planner_data={"weekly": {"headers": ["B"]}},
		)
		self.client.force_login(self.allowed_user)
		response = self.client.post(
			reverse("turni_planner_home"),
			{"action": "delete_week", "week_label": state.week_label},
		)

		self.assertRedirects(response, reverse("turni_planner_home"))
		self.assertFalse(TurniPlannerWeekState.objects.filter(week_label=state.week_label).exists())
		self.assertTrue(TurniPlannerWeekState.objects.filter(week_label="Week 29 da Lunedi 13/07/2026 a Sabato 18/07/2026").exists())


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


class PayslipBulkDeleteTests(TestCase):
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
			username="staff.delete",
			password="Password123!",
			is_staff=True,
		)
		self.client.force_login(self.admin_user)

		self.employee_user = get_user_model().objects.create_user(
			username="maggio.user",
			password="Password123!",
		)
		self.employee = Employee.objects.create(
			user=self.employee_user,
			first_name="Mario",
			last_name="Rossi",
		)
		self.other_employee_user = get_user_model().objects.create_user(
			username="giugno.user",
			password="Password123!",
		)
		self.other_employee = Employee.objects.create(
			user=self.other_employee_user,
			first_name="Anna",
			last_name="Verdi",
		)

	def _create_payslip(self, employee, year, month, name):
		return Payslip.objects.create(
			employee=employee,
			year=year,
			month=month,
			pdf=SimpleUploadedFile(name, b"%PDF-1.4\n%test pdf\n", content_type="application/pdf"),
		)

	def test_admin_all_payslips_can_delete_filtered_month(self):
		may_one = self._create_payslip(self.employee, 2026, 5, "maggio-1.pdf")
		may_two = self._create_payslip(self.other_employee, 2026, 5, "maggio-2.pdf")
		june_one = self._create_payslip(self.employee, 2026, 6, "giugno-1.pdf")

		response = self.client.post(
			reverse("admin_all_payslips"),
			{
				"action": "bulk_delete_payslips",
				"year": "2026",
				"month": "5",
				"employee": "",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "2 cedolini eliminati definitivamente.")
		self.assertFalse(Payslip.objects.filter(id=may_one.id).exists())
		self.assertFalse(Payslip.objects.filter(id=may_two.id).exists())
		self.assertTrue(Payslip.objects.filter(id=june_one.id).exists())

	def test_delete_payslips_command_supports_dry_run_and_confirmed_delete(self):
		may_one = self._create_payslip(self.employee, 2026, 5, "cmd-maggio-1.pdf")
		may_two = self._create_payslip(self.other_employee, 2026, 5, "cmd-maggio-2.pdf")
		self._create_payslip(self.employee, 2026, 6, "cmd-giugno-1.pdf")

		dry_run_output = StringIO()
		call_command("delete_payslips", year=2026, month=5, dry_run=True, stdout=dry_run_output)
		self.assertIn("Cedolini trovati: 2", dry_run_output.getvalue())
		self.assertTrue(Payslip.objects.filter(id=may_one.id).exists())
		self.assertTrue(Payslip.objects.filter(id=may_two.id).exists())

		delete_output = StringIO()
		call_command("delete_payslips", year=2026, month=5, yes=True, stdout=delete_output)
		self.assertIn("Cancellazione completata.", delete_output.getvalue())
		self.assertFalse(Payslip.objects.filter(id=may_one.id).exists())
		self.assertFalse(Payslip.objects.filter(id=may_two.id).exists())
		self.assertEqual(Payslip.objects.filter(year=2026, month=6).count(), 1)

	def test_open_payslip_redirect_adds_cache_buster(self):
		payslip = self._create_payslip(self.employee, 2026, 5, "cache-maggio.pdf")
		self.client.force_login(self.employee_user)

		response = self.client.get(reverse("open_payslip", args=[payslip.id]))

		self.assertEqual(response.status_code, 302)
		self.assertIn("/payslips/", response["Location"])
		self.assertIn(f"v={payslip.id}-", response["Location"])


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
