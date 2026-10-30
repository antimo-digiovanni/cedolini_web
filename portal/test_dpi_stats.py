from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import DpiDelivery, DpiReplacementRule, Employee


class DpiStatsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('capo', password='x', is_staff=True)
        u = User.objects.create_user('mario', password='x')
        self.emp = Employee.objects.create(user=u, first_name='Mario', last_name='Rossi', must_change_password=False)
        today = timezone.localdate()
        DpiDelivery.objects.create(employee=self.emp, status='signed', delivered_on=today - timedelta(days=30),
                                   items=[{'label': 'Scarpe di sicurezza', 'qty': 1, 'text': 'Scarpe di sicurezza'},
                                          {'label': 'Casco', 'qty': 1, 'text': 'Casco n. 1'}])
        DpiDelivery.objects.create(employee=self.emp, status='signed', delivered_on=today - timedelta(days=45),
                                   items=[{'label': 'Guanti anti-taglio', 'qty': 1, 'text': 'Guanti anti-taglio'}])
        DpiDelivery.objects.create(employee=self.emp, status='signed', delivered_on=today - timedelta(days=200),
                                   items=[{'label': 'Scarpe di sicurezza', 'qty': 1, 'text': 'Scarpe di sicurezza'}])
        DpiDelivery.objects.create(employee=self.emp, status='cancelled', delivered_on=today,
                                   items=[{'label': 'Guanti anti-taglio', 'qty': 1, 'text': 'x'}])

    def test_summary_states(self):
        from .dpi_stats import summary
        items = {i['label']: i for i in summary(self.emp)}
        scarpe = items['Scarpe di sicurezza']
        self.assertEqual(scarpe['days'], 30)
        self.assertEqual(scarpe['state'], 'early')
        self.assertEqual(scarpe['count'], 2)
        self.assertEqual(scarpe['year_times'], 2)
        self.assertEqual(items['Guanti anti-taglio']['state'], 'ok')  # 45 giorni > 30
        self.assertEqual(items['Pantaloni']['state'], 'never')
        self.assertEqual(items['Casco']['state'], 'info')  # voce a mano, senza durata
        DpiReplacementRule.objects.create(label='Guanti anti-taglio', days=60)
        self.assertEqual({i['label']: i for i in summary(self.emp)}['Guanti anti-taglio']['state'], 'early')

    def test_views(self):
        url = reverse('admin_dpi_summary', args=[self.emp.id])
        self.client.force_login(self.emp.user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        r = self.client.get(url)
        self.assertContains(r, '30 giorni fa')
        self.assertContains(r, 'Troppo presto')
        self.assertContains(r, 'Mai consegnato')
        self.assertContains(self.client.get(reverse('admin_dpi')), 'Ogni quanto si può ridare un DPI')
        self.client.post(reverse('admin_dpi_rules'), {'days_scarpe_di_sicurezza': '20'})
        self.assertEqual(DpiReplacementRule.objects.get(label='Scarpe di sicurezza').days, 20)
        self.assertContains(self.client.get(reverse('admin_employee_detail', args=[self.emp.id])), 'Situazione DPI')
