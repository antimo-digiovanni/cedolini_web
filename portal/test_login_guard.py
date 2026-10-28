from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .login_guard import MAX_PER_ACCOUNT
from .models import LoginThrottle


class LoginGuardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('mario', password='Giusta123!')

    def _login(self, password, username='mario'):
        return self.client.post(reverse('login'), {'username': username, 'password': password})

    def test_lock_after_too_many_failures_then_correct_password_refused(self):
        for _ in range(MAX_PER_ACCOUNT - 1):
            r = self._login('sbagliata')
            self.assertContains(r, 'Accesso non riuscito')
        r = self._login('sbagliata')
        self.assertContains(r, 'Troppi tentativi non riusciti')
        r = self._login('Giusta123!')  # anche quella giusta è bloccata per qualche minuto
        self.assertContains(r, 'Troppi tentativi non riusciti')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_success_resets_counter(self):
        for _ in range(3):
            self._login('sbagliata')
        r = self._login('Giusta123!')
        self.assertEqual(r.status_code, 302)
        self.assertFalse(LoginThrottle.objects.filter(key='u:mario').exists())

    def test_lock_is_per_account(self):
        User.objects.create_user('luigi', password='Giusta123!')
        for _ in range(MAX_PER_ACCOUNT):
            self._login('sbagliata')
        self.assertEqual(self._login('Giusta123!', username='luigi').status_code, 302)

    def test_username_case_insensitive_key(self):
        for _ in range(MAX_PER_ACCOUNT):
            self._login('sbagliata', username='MARIO')
        self.assertContains(self._login('Giusta123!'), 'Troppi tentativi')
