import json
from html.parser import HTMLParser

from django.test import SimpleTestCase, override_settings
from django.urls import reverse


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings = 0
        self.canonical = None
        self.schemas = []
        self.schema_text = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'h1':
            self.headings += 1
        if tag == 'link' and attributes.get('rel') == 'canonical':
            self.canonical = attributes.get('href')
        if tag == 'script' and attributes.get('type') == 'application/ld+json':
            self.schema_text = ''

    def handle_data(self, data):
        if self.schema_text is not None:
            self.schema_text += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.schema_text is not None:
            self.schemas.append(json.loads(self.schema_text))
            self.schema_text = None


@override_settings(SECURE_SSL_REDIRECT=False, STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class PestControlTests(SimpleTestCase):
    def test_anonymous_visitors_can_read_page_without_group_redirect(self):
        response = self.client.get(reverse('public_pest_control') + '?utm_source=google')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'site/pest_control.html')
        self.assertContains(response, 'Disinfestazione blatte')
        self.assertContains(response, 'ratti e topi')
        self.assertContains(response, 'tel:+393400515648')
        self.assertNotContains(response, 'tel:+390818801972')
        self.assertNotContains(response, 'noindex')
        parser = PageParser()
        parser.feed(response.content.decode())
        self.assertEqual(parser.headings, 1)
        self.assertEqual(parser.canonical, 'https://www.sanvincenzoservice.it/disinfestazione-derattizzazione/')
        self.assertTrue(any(schema.get('@type') == 'Service' for schema in parser.schemas))
        service = next(schema for schema in parser.schemas if schema.get('@type') == 'Service')
        self.assertEqual(service['provider']['telephone'], '+393400515648')

    def test_sitemap_contains_indexable_service_page(self):
        self.assertContains(self.client.get('/sitemap.xml'), '/disinfestazione-derattizzazione/</loc>')

    def test_existing_service_page_links_to_pest_control(self):
        from django.template.loader import render_to_string

        html = render_to_string('site/services.html', request=None)
        self.assertIn(reverse('public_pest_control'), html)