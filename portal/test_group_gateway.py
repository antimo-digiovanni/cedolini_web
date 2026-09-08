from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse

from .group_gateway import GroupGatewayMiddleware, PUBLIC_PATHS, select_san_vincenzo


@override_settings(SECURE_SSL_REDIRECT=False)
class GroupGatewayTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = GroupGatewayMiddleware(lambda request: HttpResponse('company'))

    def request(self, path, selected=False, authenticated=False):
        request = self.factory.get(path)
        request.user = SimpleNamespace(is_authenticated=authenticated)
        request.session = {'san_vincenzo_selected': selected}
        return request

    def test_public_entry_requires_choice(self):
        for path in PUBLIC_PATHS:
            with self.subTest(path=path):
                response = self.middleware(self.request(path))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse('group_home'))
                self.assertIn('no-store', response['Cache-Control'])

    def test_choice_allows_company_navigation(self):
        request = self.request('/azienda/san-vincenzo/')
        response = select_san_vincenzo(request)
        self.assertEqual(response.url, reverse('public_home'))
        request.path = '/sito-web/'
        self.assertEqual(self.middleware(request).status_code, 200)

    def test_portal_login_and_authenticated_users_are_not_gated(self):
        for path in ['/login/', '/portal/', '/admin/', '/gruppo/', '/robots.txt']:
            self.assertEqual(self.middleware(self.request(path)).status_code, 200)
        self.assertEqual(self.middleware(self.request('/sito-web/', authenticated=True)).status_code, 200)

    def test_posts_are_not_redirected(self):
        request = self.request('/contatti/')
        request.method = 'POST'
        self.assertEqual(self.middleware(request).status_code, 200)

    def test_group_page_and_assets(self):
        response = self.client.get('/gruppo/')
        self.assertContains(response, 'Gruppo Di Giovanni')
        self.assertContains(response, '?azienda=timmy-gel')
        self.assertEqual(self.client.get('/gruppo/logo-gruppo.svg').status_code, 200)
        self.assertEqual(self.client.get('/gruppo/README.md').status_code, 404)

    def test_root_preserves_employee_redirect(self):
        from .views import home

        self.assertEqual(home(self.request('/')).url, reverse('group_home'))
        with patch('portal.views.user_home_url_name', return_value='login') as destination:
            self.assertEqual(home(self.request('/', authenticated=True)).url, reverse('login'))
            destination.assert_called_once()

    def test_sitemap_lists_group_instead_of_redirecting_pages(self):
        response = self.client.get('/sitemap.xml')
        self.assertContains(response, '/gruppo/</loc>')
        self.assertNotContains(response, '/chi-siamo/</loc>')