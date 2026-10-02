from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from .models import Employee


class PortalThemeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "Demo-tests-only-2026!"
        cls.admin = get_user_model().objects.create_user(
            username="theme-admin", password=cls.password, is_staff=True,
        )
        cls.employee_user = get_user_model().objects.create_user(
            username="theme-employee", email="employee@example.test", password=cls.password,
            first_name="Mario", last_name="Rossi",
        )
        cls.employee = Employee.objects.create(
            user=cls.employee_user, first_name="Mario", last_name="Rossi",
            must_change_password=False, privacy_accepted=True,
        )

    def test_login_preserves_next_and_has_accessible_fields(self):
        response = self.client.get(reverse("login"), {"next": reverse("timekeeping")})
        self.assertContains(response, 'value="/portal/marcatura/"')
        for text in ('for="id_username"', 'for="id_password"', 'autocomplete="current-password"', 'aria-label="Mostra password"', 'name="csrfmiddlewaretoken"'):
            self.assertContains(response, text)

    def test_invalid_login_preserves_username_not_password(self):
        response = self.client.post(reverse("login"), {"username": "unknown-user", "password": "must-not-be-rendered"})
        self.assertContains(response, "Accesso non riuscito")
        self.assertContains(response, 'value="unknown-user"')
        self.assertNotContains(response, "must-not-be-rendered")

    def test_login_for_both_roles(self):
        for user, destination in ((self.admin, "admin_dashboard"), (self.employee_user, "dashboard")):
            with self.subTest(user=user.username):
                client = Client()
                response = client.post(reverse("login"), {
                    "username": user.username, "password": self.password, "next": reverse(destination),
                })
                self.assertRedirects(response, reverse(destination))
                self.assertEqual(int(client.session["_auth_user_id"]), user.pk)

    def test_login_with_email(self):
        response = self.client.post(reverse("login"), {
            "username": self.employee_user.email, "password": self.password, "next": reverse("dashboard"),
        })
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_rejects_missing_csrf(self):
        response = Client(enforce_csrf_checks=True).post(reverse("login"), {
            "username": self.admin.username, "password": self.password,
        })
        self.assertEqual(response.status_code, 403)

    def test_login_does_not_redirect_to_external_next(self):
        response = self.client.post(reverse("login"), {
            "username": self.admin.username, "password": self.password, "next": "https://example.org/",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.url.startswith("https://example.org"))

    def test_admin_pages_use_shared_theme(self):
        self.client.force_login(self.admin)
        for name in (
            "admin_dashboard", "admin_employees", "admin_all_payslips", "admin_report",
            "admin_timekeeping", "admin_out_of_zone_requests", "admin_vacation_requests",
            "admin_work_zones", "admin_audit_events", "admin_import_jobs", "admin_payslip_integrity",
            "admin_upload_period_folder", "admin_upload_cud", "turni_planner_home",
            "password_change", "password_change_done",
        ):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, "portal/portal-theme.")
                self.assertContains(response, 'id="portal-main"')

    def test_employee_pages_keep_permissions_and_theme(self):
        self.client.force_login(self.employee_user)
        for name in ("dashboard", "timekeeping", "portal_tutorial", "password_change"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, "portal/portal-theme.")
                self.assertNotContains(response, 'href="/portal/admin-employees/"')
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "La tua area personale")

    def test_recovery_pages_do_not_fall_back_to_django_admin(self):
        for name in ("password_reset", "password_reset_done", "password_reset_complete"):
            with self.subTest(page=name):
                self.assertContains(self.client.get(reverse(name)), "auth-brand-header")
        response = self.client.get(reverse("password_reset_confirm", kwargs={"uidb64": "invalid", "token": "invalid"}))
        self.assertContains(response, "Richiedi nuovo link")
        self.assertContains(response, "auth-brand-header")

    def test_password_reset_keeps_email_delivery(self):
        response = self.client.post(reverse("password_reset"), {"email": self.employee_user.email})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.employee_user.email])

    def test_password_change_keeps_session(self):
        self.client.force_login(self.employee_user)
        response = self.client.post(reverse("password_change"), {
            "old_password": self.password,
            "new_password1": "New-demo-tests-only-2026!",
            "new_password2": "New-demo-tests-only-2026!",
        })
        self.assertRedirects(response, reverse("password_change_done"))
        self.employee_user.refresh_from_db()
        self.assertTrue(self.employee_user.check_password("New-demo-tests-only-2026!"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.employee_user.pk)