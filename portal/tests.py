from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase


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
