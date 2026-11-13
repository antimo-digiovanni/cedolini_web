import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .access import PATRIMONIO_GROUP_NAME
from .card_cycle import current_cycle
from .models import CorporateCardEntry, PlannedCorporateCardExpense

PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00'
       b'\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82')


class CardCycleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('carta', password='x')
        Group.objects.get_or_create(name=PATRIMONIO_GROUP_NAME)[0].user_set.add(self.user)
        self.client.force_login(self.user)
        self.url = reverse('personal_asset_dashboard')
        d = datetime.date
        self.add('top_up', 300, d(2026, 10, 1), 'Ricarica datore')
        self.add('expense', 250, d(2026, 10, 5), 'Vecchia spesa')
        self.add('top_up', 400, d(2026, 11, 2), 'Ricarica datore')
        self.add('expense', 80, d(2026, 11, 3), 'Carburante')
        self.add('withdrawal', 20, d(2026, 11, 4), 'Contanti')
        PlannedCorporateCardExpense.objects.create(user=self.user, planned_on=d(2026, 11, 10), category='Guanti', amount=Decimal('500'))

    def add(self, kind, amount, day, cat):
        return CorporateCardEntry.objects.create(user=self.user, operation_type=kind, amount=Decimal(amount), occurred_on=day, category=cat)

    def test_cycle_numbers(self):
        c = current_cycle(self.user)
        self.assertEqual(c['top'].amount, Decimal('400'))
        self.assertEqual(c['spent'], Decimal('100'))
        self.assertEqual(c['balance'], Decimal('350'))
        self.assertEqual(c['carry_over'], Decimal('50'))
        self.assertEqual([e.category for e in c['expenses']], ['Contanti', 'Carburante'])
        self.assertEqual(c['request_amount'], Decimal('150'))

    def test_page_shows_cycle(self):
        r = self.client.get(self.url)
        self.assertContains(r, 'Chiedi ricarica')
        self.assertContains(r, 'Spese dall\'ultima ricarica')
        self.assertContains(r, 'Storico, controllo banca e strumenti')

    def test_request_pdf(self):
        e = CorporateCardEntry.objects.get(category='Carburante')
        e.receipt_image = SimpleUploadedFile('s.png', PNG, content_type='image/png')
        e.save()
        r = self.client.get(self.url + '?report=richiesta_ricarica')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))

    def test_buy_planned_creates_expense(self):
        p = PlannedCorporateCardExpense.objects.get()
        p.amount = Decimal('300'); p.save()
        r = self.client.post(self.url, {'action': 'buy_planned_expense', 'planned_expense_id': p.id, 'operation_type': 'expense',
                                        'category': 'Guanti', 'amount': '280.50', 'occurred_on': '2026-11-12', 'payment_method': 'company_card'})
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertIsNotNone(p.paid_entry)
        self.assertEqual(p.paid_entry.amount, Decimal('280.50'))
        c = current_cycle(self.user)
        self.assertEqual(c['planned'], [])
        self.assertEqual(c['balance'], Decimal('69.50'))

    def test_buy_over_balance_refused(self):
        p = PlannedCorporateCardExpense.objects.get()
        r = self.client.post(self.url, {'action': 'buy_planned_expense', 'planned_expense_id': p.id, 'operation_type': 'expense',
                                        'category': 'Guanti', 'amount': '500', 'occurred_on': '2026-11-12'})
        self.assertEqual(r.status_code, 200)
        p.refresh_from_db()
        self.assertIsNone(p.paid_entry)

    def test_top_up_starts_new_cycle(self):
        self.client.post(self.url, {'action': 'create_corporate_card_entry', 'operation_type': 'top_up', 'category': 'Ricarica datore',
                                    'amount': '150', 'occurred_on': '2026-11-13'})
        c = current_cycle(self.user)
        self.assertEqual(c['top'].amount, Decimal('150'))
        self.assertEqual(c['spent'], Decimal('0'))
        self.assertEqual(c['balance'], Decimal('500'))
        self.assertEqual(c['request_amount'], Decimal('0'))

    def test_other_user_cannot_buy(self):
        other = get_user_model().objects.create_user('altro', password='x')
        Group.objects.get(name=PATRIMONIO_GROUP_NAME).user_set.add(other)
        self.client.force_login(other)
        p = PlannedCorporateCardExpense.objects.get()
        self.client.post(self.url, {'action': 'buy_planned_expense', 'planned_expense_id': p.id, 'operation_type': 'expense',
                                    'category': 'Guanti', 'amount': '10'})
        p.refresh_from_db()
        self.assertIsNone(p.paid_entry)
