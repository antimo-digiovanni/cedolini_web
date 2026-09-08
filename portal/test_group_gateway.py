from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse

from .group_gateway import select_san_vincenzo


@override_settings(SECURE_SSL_REDIRECT=False, STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class GroupGatewayTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request(self, path, selected=False, authenticated=False):
        request = self.factory.get(path)
        request.user = SimpleNamespace(is_authenticated=authenticated)
        request.session = {'san_vincenzo_selected': selected}
        return request

    def test_public_pages_open_directly(self):
        for path in ['/', '/sito-web/', '/chi-siamo/', '/servizi/', '/servizi-digitali/', '/macchinari/', '/contatti/']:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'href="/gruppo/"')

    def test_choice_allows_company_navigation(self):
        request = self.request('/azienda/san-vincenzo/')
        response = select_san_vincenzo(request)
        self.assertEqual(response.url, reverse('public_home'))
        self.assertFalse(request.session['san_vincenzo_selected'])

    def test_group_page_and_assets(self):
        response = self.client.get('/gruppo/')
        self.assertContains(response, 'Gruppo Di Giovanni')
        self.assertContains(response, 'https://www.timmygel.com/index.html')
        self.assertNotContains(response, '?azienda=')
        self.assertEqual(self.client.get('/gruppo/logo-gruppo.svg').status_code, 200)
        self.assertEqual(self.client.get('/gruppo/README.md').status_code, 404)

    def test_root_preserves_employee_redirect(self):
        from .views import home

        self.assertEqual(home(self.request('/')).status_code, 200)
        with patch('portal.views.user_home_url_name', return_value='login') as destination:
            self.assertEqual(home(self.request('/', authenticated=True)).url, reverse('login'))
            destination.assert_called_once()

    def test_sitemap_lists_group_and_company_pages(self):
        response = self.client.get('/sitemap.xml')
        self.assertContains(response, '/gruppo/</loc>')
        self.assertContains(response, '/chi-siamo/</loc>')