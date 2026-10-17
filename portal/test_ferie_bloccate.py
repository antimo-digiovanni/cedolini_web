from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Employee, VacationRequest
from .views import _vacation_blocked_dates


class FerieBloccateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('mario', password='x')
        self.employee = Employee.objects.create(user=self.user, first_name='Mario', last_name='Rossi',
                                                must_change_password=False, privacy_accepted=True)
        self.client.force_login(self.user)

    def _request(self, start, end):
        return self.client.post(reverse('dashboard'), {
            'action': 'request_vacation', 'start_date': start.isoformat(), 'end_date': end.isoformat(),
            'multiple_days': 'on', 'vacation_reason': 'Ferie natalizie con la famiglia.',
        })

    def test_blocked_dates_detected(self):
        self.assertEqual(_vacation_blocked_dates(date(2026, 12, 24), date(2026, 12, 24)), [date(2026, 12, 24)])
        self.assertEqual(_vacation_blocked_dates(date(2026, 12, 22), date(2027, 1, 2)), [date(2026, 12, 24), date(2026, 12, 31)])
        self.assertEqual(_vacation_blocked_dates(date(2026, 12, 25), date(2026, 12, 30)), [])

    def test_request_including_24_or_31_is_refused(self):
        for start, end in [(date(2026, 12, 24), date(2026, 12, 24)), (date(2026, 12, 29), date(2027, 1, 3))]:
            r = self._request(start, end)
            self.assertIn('vacation_status=blocked_day', r['Location'])
        self.assertFalse(VacationRequest.objects.exists())

    def test_other_days_still_allowed(self):
        r = self._request(date(2026, 12, 27), date(2026, 12, 30))
        self.assertNotIn('blocked_day', r['Location'])
