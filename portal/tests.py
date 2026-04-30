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

from .access import TODAY_MARKINGS_GROUP_NAME, TURNI_PLANNER_GROUP_NAME
from .models import Cud, Employee, ImportJob, Payslip, SmartAgendaItem, SmartAgendaMessage, TurniPlannerWeekState, VacationRequest, WorkSession


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

	def test_today_markings_shows_secretary_widget_for_antimo_account(self):
		self.owner_user.first_name = "Antimo"
		self.owner_user.save(update_fields=["first_name"])
		SmartAgendaItem.objects.create(
			owner=self.owner_user,
			title="Controllare le priorita del giorno",
			status=SmartAgendaItem.STATUS_OPEN,
			is_daily=True,
			priority=SmartAgendaItem.PRIORITY_HIGH,
		)

		self.client.force_login(self.owner_user)
		response = self.client.get(reverse("today_markings_dashboard"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Segretaria del giorno")
		self.assertContains(response, "Controllare le priorita del giorno")
		self.assertContains(response, "Quotidiani")
		self.assertContains(response, "Da fare oggi")
		self.assertContains(response, "In ritardo")


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


class SmartAgendaTests(TestCase):
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

	def test_smart_agenda_is_reserved_to_antimo_account(self):
		self.client.force_login(self.other_user)
		response = self.client.get(reverse("smart_agenda"))
		self.assertEqual(response.status_code, 403)

	def test_smart_agenda_allows_antimo_by_first_name(self):
		antimo_named_user = get_user_model().objects.create_user(
			username="admin.1",
			first_name="Antimo",
			password="Password123!",
		)
		self.client.force_login(antimo_named_user)
		response = self.client.get(reverse("smart_agenda"))
		self.assertEqual(response.status_code, 200)

	def test_smart_agenda_creates_reminder_from_prompt(self):
		self.client.force_login(self.antimo_user)
		response = self.client.post(
			reverse("smart_agenda"),
			{
				"action": "ask",
				"prompt": "Ricordami lavaggio critico della linea, chiediamo 700€ domani",
			},
		)

		self.assertRedirects(response, reverse("smart_agenda"))
		item = SmartAgendaItem.objects.get(owner=self.antimo_user)
		self.assertIn("lavaggio critico", item.title.lower())
		self.assertEqual(str(item.quoted_amount), "700.00")
		self.assertEqual(item.remind_on, timezone.localdate() + timezone.timedelta(days=1))
		self.assertEqual(SmartAgendaMessage.objects.filter(owner=self.antimo_user).count(), 2)

	def test_smart_agenda_creates_daily_task_with_time(self):
		self.client.force_login(self.antimo_user)
		response = self.client.post(
			reverse("smart_agenda"),
			{
				"action": "ask",
				"prompt": "Ricordami ogni giorno di controllare i messaggi alle 08:30",
			},
		)

		self.assertRedirects(response, reverse("smart_agenda"))
		item = SmartAgendaItem.objects.filter(owner=self.antimo_user).latest("created_at")
		self.assertTrue(item.is_daily)
		self.assertIsNone(item.remind_on)
		self.assertEqual(item.remind_time.strftime("%H:%M"), "08:30")

	def test_smart_agenda_creates_precise_date_and_priority(self):
		self.client.force_login(self.antimo_user)
		response = self.client.post(
			reverse("smart_agenda"),
			{
				"action": "ask",
				"prompt": "Segnami urgente: il 24/04 alle 15 chiama il cliente per il lavaggio critico della linea",
			},
		)

		self.assertRedirects(response, reverse("smart_agenda"))
		item = SmartAgendaItem.objects.filter(owner=self.antimo_user).latest("created_at")
		self.assertEqual(item.priority, SmartAgendaItem.PRIORITY_URGENT)
		self.assertEqual(item.remind_on.strftime("%d/%m"), "24/04")
		self.assertEqual(item.remind_time.strftime("%H:%M"), "15:00")


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

	def test_home_redirects_turni_planner_user_to_planner(self):
		self.client.force_login(self.allowed_user)
		response = self.client.get(reverse("home"))
		self.assertRedirects(response, reverse("turni_planner_home"))

	def test_turni_planner_denies_non_authorized_user(self):
		self.client.force_login(self.denied_user)
		response = self.client.get(reverse("turni_planner_home"))
		self.assertEqual(response.status_code, 403)

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

	def test_turni_planner_new_week_clones_latest_planner_data(self):
		previous_state = TurniPlannerWeekState.objects.create(
			week_label="Week 17: da Lunedi 20/04/2026 a Venerdi 24/04/2026",
			planner_data={
				"weekly": {
					"headers": [f"Reparto {index}" for index in range(1, 11)],
					"central_departments": [""] * 10,
					"sections": [
						{
							"label": "1 turno",
							"time_values": ["06:00"] * 10,
							"rows": [["Mario"] * 10, ["Luigi"] * 10, ["Anna"] * 10],
						},
						{
							"label": "2 turno",
							"time_values": ["14:00"] * 10,
							"rows": [["Paolo"] * 10, ["Gina"] * 10, ["Luca"] * 10],
						},
						{
							"label": "3 turno",
							"time_values": ["22:00"] * 10,
							"rows": [["Sara"] * 10, ["Piero"] * 10, ["Marta"] * 10],
						},
						{
							"label": "4 turno",
							"time_values": ["00:00"] * 10,
							"rows": [["Notte A"] * 10, ["Notte B"] * 10, ["Notte C"] * 10],
						},
					],
				},
				"saturday": {
					"base_date": "25/04/2026",
					"rows": [["25/04/2026", "Mattina", "Mario", "Capo A", "Lavaggio", "Reparto A"]],
				},
				"sunday": {
					"base_date": "26/04/2026",
					"rows": [["26/04/2026", "Sera", "Luigi", "Capo B", "Controllo", "Reparto B"]],
				},
				"portineria_weekly": {
					"headers": ["Portineria Centrale", "Centralinista", "Portineria Cella"],
					"sections": [
						{"label": "1 turno", "time_values": ["06:14", "08:17", "06:14"], "rows": [["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]]},
						{"label": "2 turno", "time_values": ["14:22", "", "14:22"], "rows": [["L", "M", "N"], ["O", "P", "Q"], ["R", "S", "T"]]},
						{"label": "3 turno", "time_values": ["22:06", "", "22:06"], "rows": [["U", "V", "Z"], ["AA", "AB", "AC"], ["AD", "AE", "AF"]]},
					],
				},
				"portineria_weekend": {
					"base_date": "25/04/2026",
					"rows": [["25/04/2026", "Mattina", "Port A", "Resp A", "Controllo", "Portineria"]],
				},
			},
			updated_by=self.allowed_user,
		)

		self.client.force_login(self.allowed_user)
		new_week_label = "Week 19: da Lunedi 04/05/2026 a Venerdi 08/05/2026"
		response = self.client.post(
			reverse("turni_planner_home"),
			{"action": "open_week", "week_label": new_week_label},
		)

		new_state = TurniPlannerWeekState.objects.get(week_label=new_week_label)
		previous_state.refresh_from_db()
		self.assertRedirects(response, f"{reverse('turni_planner_home')}?week={new_state.week_label}")
		self.assertEqual(new_state.updated_by, self.allowed_user)
		self.assertEqual(new_state.planner_data, previous_state.planner_data)
		self.assertIsNot(new_state.planner_data, previous_state.planner_data)

	def test_turni_planner_open_week_backfills_existing_empty_week_from_latest_non_empty_state(self):
		previous_state = TurniPlannerWeekState.objects.create(
			week_label="Week 17: da Lunedi 20/04/2026 a Venerdi 24/04/2026",
			planner_data={
				"weekly": {
					"headers": [f"Reparto {index}" for index in range(1, 11)],
					"central_departments": [""] * 10,
					"sections": [
						{"label": "1 turno", "time_values": ["06:00"] * 10, "rows": [["Mario"] * 10, ["Luigi"] * 10, ["Anna"] * 10]},
						{"label": "2 turno", "time_values": ["14:00"] * 10, "rows": [["Paolo"] * 10, ["Gina"] * 10, ["Luca"] * 10]},
						{"label": "3 turno", "time_values": ["22:00"] * 10, "rows": [["Sara"] * 10, ["Piero"] * 10, ["Marta"] * 10]},
						{"label": "4 turno", "time_values": ["00:00"] * 10, "rows": [["Notte A"] * 10, ["Notte B"] * 10, ["Notte C"] * 10]},
					],
				},
				"saturday": {"base_date": "25/04/2026", "rows": [["25/04/2026", "Mattina", "Mario", "Capo A", "Lavaggio", "Reparto A"]]},
			},
			updated_by=self.allowed_user,
		)
		TurniPlannerWeekState.objects.create(
			week_label="WEEK 18",
			planner_data={},
			updated_by=self.allowed_user,
		)
		empty_state = TurniPlannerWeekState.objects.create(
			week_label="Week 19: da Lunedì 04/05/2026 a Venerdì 08/05/2026",
			planner_data={},
		)

		self.client.force_login(self.allowed_user)
		response = self.client.post(
			reverse("turni_planner_home"),
			{"action": "open_week", "week_label": empty_state.week_label},
		)

		empty_state.refresh_from_db()
		previous_state.refresh_from_db()
		self.assertRedirects(response, f"{reverse('turni_planner_home')}?week={empty_state.week_label}")
		self.assertEqual(empty_state.planner_data, previous_state.planner_data)

	def test_turni_planner_saves_shared_planner_data(self):
		state = TurniPlannerWeekState.objects.create(
			week_label="Week 29 da Lunedi 13/07/2026 a Sabato 18/07/2026",
			planner_data={},
		)
		self.client.force_login(self.allowed_user)
		response = self.client.post(
			reverse("turni_planner_home"),
			{
				"action": "save_planner",
				"week_label": state.week_label,
				"weekly_headers": [f"Reparto {index}" for index in range(1, 11)],
				"weekly_time_0": ["06:00"] * 10,
				"weekly_time_1": ["14:00"] * 10,
				"weekly_time_2": ["22:00"] * 10,
				"weekly_time_3": ["00:00"] * 10,
				"weekly_row_0_0": ["Mario"] * 10,
				"weekly_row_0_1": ["Luigi"] * 10,
				"weekly_row_0_2": ["Anna"] * 10,
				"weekly_row_1_0": ["Paolo"] * 10,
				"weekly_row_1_1": ["Gina"] * 10,
				"weekly_row_1_2": ["Luca"] * 10,
				"weekly_row_2_0": ["Sara"] * 10,
				"weekly_row_2_1": ["Piero"] * 10,
				"weekly_row_2_2": ["Marta"] * 10,
				"weekly_row_3_0": ["Notte A"] * 10,
				"weekly_row_3_1": ["Notte B"] * 10,
				"weekly_row_3_2": ["Notte C"] * 10,
				"saturday_base_date": "18/07/2026",
				"saturday_row_0": ["18/07/2026", "Mattina", "Mario", "Capo A", "Lavaggio", "Reparto A"],
				"sunday_base_date": "19/07/2026",
				"sunday_row_0": ["19/07/2026", "Notte", "Luigi", "Capo B", "Sanificazione", "Reparto B"],
				"portineria_weekly_headers": ["Portineria Centrale", "Centralinista", "Portineria Cella"],
				"portineria_weekly_time_0": ["06:14", "08:17", "06:14"],
				"portineria_weekly_time_1": ["14:22", "", "14:22"],
				"portineria_weekly_time_2": ["22:06", "", "22:06"],
				"portineria_weekly_row_0_0": ["Persona A", "Persona B", "Persona C"],
				"portineria_weekly_row_0_1": ["Persona D", "Persona E", "Persona F"],
				"portineria_weekly_row_0_2": ["Persona G", "Persona H", "Persona I"],
				"portineria_weekly_row_1_0": ["Persona L", "Persona M", "Persona N"],
				"portineria_weekly_row_1_1": ["Persona O", "Persona P", "Persona Q"],
				"portineria_weekly_row_1_2": ["Persona R", "Persona S", "Persona T"],
				"portineria_weekly_row_2_0": ["Persona U", "Persona V", "Persona Z"],
				"portineria_weekly_row_2_1": ["Persona AA", "Persona AB", "Persona AC"],
				"portineria_weekly_row_2_2": ["Persona AD", "Persona AE", "Persona AF"],
				"portineria_weekend_base_date": "18/07/2026",
				"portineria_weekend_row_0": ["18/07/2026", "Mattina", "Port A", "Resp A", "Controllo", "Portineria"],
			},
		)

		state.refresh_from_db()
		self.assertRedirects(response, f"{reverse('turni_planner_home')}?week={state.week_label}")
		self.assertEqual(state.updated_by, self.allowed_user)
		self.assertEqual(state.planner_data["weekly"]["headers"][0], "Reparto 1")
		self.assertEqual(state.planner_data["weekly"]["sections"][0]["rows"][0][0], "Mario")
		self.assertEqual(state.planner_data["weekly"]["sections"][3]["rows"][2][9], "Notte C")
		self.assertEqual(state.planner_data["saturday"]["base_date"], "18/07/2026")
		self.assertEqual(state.planner_data["saturday"]["rows"][0][2], "Mario")
		self.assertEqual(state.planner_data["sunday"]["rows"][0][4], "Sanificazione")
		self.assertEqual(state.planner_data["portineria_weekly"]["sections"][0]["rows"][0][1], "Persona B")
		self.assertEqual(state.planner_data["portineria_weekend"]["rows"][0][5], "Portineria")

	def test_turni_planner_saves_dynamic_weekend_row_counts(self):
		state = TurniPlannerWeekState.objects.create(
			week_label="Week 29 bis da Lunedi 13/07/2026 a Sabato 18/07/2026",
			planner_data={},
		)
		self.client.force_login(self.allowed_user)
		response = self.client.post(
			reverse("turni_planner_home"),
			{
				"action": "save_planner",
				"week_label": state.week_label,
				"weekly_headers": [f"Reparto {index}" for index in range(1, 11)],
				"weekly_time_0": [""] * 10,
				"weekly_time_1": [""] * 10,
				"weekly_time_2": [""] * 10,
				"weekly_time_3": [""] * 10,
				"weekly_row_0_0": [""] * 10,
				"weekly_row_0_1": [""] * 10,
				"weekly_row_0_2": [""] * 10,
				"weekly_row_1_0": [""] * 10,
				"weekly_row_1_1": [""] * 10,
				"weekly_row_1_2": [""] * 10,
				"weekly_row_2_0": [""] * 10,
				"weekly_row_2_1": [""] * 10,
				"weekly_row_2_2": [""] * 10,
				"weekly_row_3_0": [""] * 10,
				"weekly_row_3_1": [""] * 10,
				"weekly_row_3_2": [""] * 10,
				"saturday_base_date": "18/07/2026",
				"saturday_row_count": "22",
				"saturday_row_0": ["18/07/2026", "Mattina", "Mario", "Capo A", "Lavaggio", "Reparto A"],
				"saturday_row_21": ["18/07/2026", "Sera", "Ultimo Sabato", "Capo Z", "Chiusura", "Reparto Z"],
				"sunday_base_date": "19/07/2026",
				"sunday_row_count": "21",
				"sunday_row_0": ["19/07/2026", "Notte", "Luigi", "Capo B", "Sanificazione", "Reparto B"],
				"sunday_row_20": ["19/07/2026", "Tardo", "Ultima Domenica", "Capo Y", "Controllo", "Reparto Y"],
				"portineria_weekly_headers": ["Portineria Centrale", "Centralinista", "Portineria Cella"],
				"portineria_weekly_time_0": ["06:14", "08:17", "06:14"],
				"portineria_weekly_time_1": ["14:22", "", "14:22"],
				"portineria_weekly_time_2": ["22:06", "", "22:06"],
				"portineria_weekly_row_0_0": ["", "", ""],
				"portineria_weekly_row_0_1": ["", "", ""],
				"portineria_weekly_row_0_2": ["", "", ""],
				"portineria_weekly_row_1_0": ["", "", ""],
				"portineria_weekly_row_1_1": ["", "", ""],
				"portineria_weekly_row_1_2": ["", "", ""],
				"portineria_weekly_row_2_0": ["", "", ""],
				"portineria_weekly_row_2_1": ["", "", ""],
				"portineria_weekly_row_2_2": ["", "", ""],
				"portineria_weekend_base_date": "18/07/2026",
				"portineria_weekend_row_0": ["18/07/2026", "Mattina", "Port A", "Resp A", "Controllo", "Portineria"],
			},
		)

		state.refresh_from_db()
		self.assertRedirects(response, f"{reverse('turni_planner_home')}?week={state.week_label}")
		self.assertEqual(len(state.planner_data["saturday"]["rows"]), 22)
		self.assertEqual(len(state.planner_data["sunday"]["rows"]), 21)
		self.assertEqual(state.planner_data["saturday"]["rows"][21][2], "Ultimo Sabato")
		self.assertEqual(state.planner_data["sunday"]["rows"][20][2], "Ultima Domenica")

	def test_turni_planner_exports_weekly_pdf_download(self):
		state = TurniPlannerWeekState.objects.create(
			week_label="Week 30 da Lunedi 20/07/2026 a Sabato 25/07/2026",
			planner_data={},
		)
		self.client.force_login(self.allowed_user)

		response = self.client.post(
			reverse("turni_planner_home"),
			{
				"action": "export_pdf_weekly",
				"week_label": state.week_label,
				"weekly_headers": [f"Reparto {index}" for index in range(1, 11)],
				"weekly_time_0": ["06:00"] * 10,
				"weekly_time_1": ["14:00"] * 10,
				"weekly_time_2": ["22:00"] * 10,
				"weekly_time_3": ["00:00"] * 10,
				"weekly_row_0_0": ["Mario"] * 10,
				"weekly_row_0_1": ["Luigi"] * 10,
				"weekly_row_0_2": ["Anna"] * 10,
				"weekly_row_1_0": ["Paolo"] * 10,
				"weekly_row_1_1": ["Gina"] * 10,
				"weekly_row_1_2": ["Luca"] * 10,
				"weekly_row_2_0": ["Sara"] * 10,
				"weekly_row_2_1": ["Piero"] * 10,
				"weekly_row_2_2": ["Marta"] * 10,
				"weekly_row_3_0": ["Notte A"] * 10,
				"weekly_row_3_1": ["Notte B"] * 10,
				"weekly_row_3_2": ["Notte C"] * 10,
				"saturday_base_date": "25/07/2026",
				"sunday_base_date": "26/07/2026",
				"portineria_weekly_headers": ["Portineria Centrale", "Centralinista", "Portineria Cella"],
				"portineria_weekly_time_0": ["06:14", "08:17", "06:14"],
				"portineria_weekly_time_1": ["14:22", "", "14:22"],
				"portineria_weekly_time_2": ["22:06", "", "22:06"],
				"portineria_weekend_base_date": "25/07/2026",
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Content-Type"], "application/pdf")
		self.assertIn("Turno settimanale.pdf", response["Content-Disposition"])
		self.assertTrue(response.content.startswith(b"%PDF"))

	def test_turni_planner_exports_portineria_weekend_jpg_download(self):
		state = TurniPlannerWeekState.objects.create(
			week_label="Week 31 da Lunedi 27/07/2026 a Sabato 01/08/2026",
			planner_data={},
		)
		self.client.force_login(self.allowed_user)

		response = self.client.post(
			reverse("turni_planner_home"),
			{
				"action": "export_jpg_portineria_weekend",
				"week_label": state.week_label,
				"weekly_headers": [""] * 10,
				"weekly_time_0": [""] * 10,
				"weekly_time_1": [""] * 10,
				"weekly_time_2": [""] * 10,
				"weekly_time_3": [""] * 10,
				"weekly_row_0_0": [""] * 10,
				"weekly_row_0_1": [""] * 10,
				"weekly_row_0_2": [""] * 10,
				"weekly_row_1_0": [""] * 10,
				"weekly_row_1_1": [""] * 10,
				"weekly_row_1_2": [""] * 10,
				"weekly_row_2_0": [""] * 10,
				"weekly_row_2_1": [""] * 10,
				"weekly_row_2_2": [""] * 10,
				"weekly_row_3_0": [""] * 10,
				"weekly_row_3_1": [""] * 10,
				"weekly_row_3_2": [""] * 10,
				"saturday_base_date": "01/08/2026",
				"sunday_base_date": "02/08/2026",
				"portineria_weekly_headers": ["Portineria Centrale", "Centralinista", "Portineria Cella"],
				"portineria_weekly_time_0": ["06:14", "08:17", "06:14"],
				"portineria_weekly_time_1": ["14:22", "", "14:22"],
				"portineria_weekly_time_2": ["22:06", "", "22:06"],
				"portineria_weekend_base_date": "01/08/2026",
				"portineria_weekend_row_0": ["01/08/2026", "Mattina", "Port A", "Resp A", "Controllo", "Portineria"],
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Content-Type"], "image/jpeg")
		self.assertIn("Comandata Sabato - Domenica e festivi Portineria.jpg", response["Content-Disposition"])
		self.assertTrue(response.content.startswith(b"\xff\xd8\xff"))


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
