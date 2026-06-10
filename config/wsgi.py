"""WSGI entrypoint.

Render may still boot the project through ``config.wsgi:application`` with a
sync Gunicorn worker. In that mode the root health check must stay on pure
Django WSGI, while ``/riconfezionamento`` is proxied to the ASGI sub-app.
"""

import os

from a2wsgi import ASGIMiddleware
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from config.asgi import RiconfezionamentoAccessMiddleware
from riconfezionamento_app.main import app as riconfezionamento_app


RICONFEZIONAMENTO_PREFIX = "/riconfezionamento"


class PathDispatcher:
	def __init__(self, django_app, riconfezionamento_wsgi_app):
		self.django_app = django_app
		self.riconfezionamento_wsgi_app = riconfezionamento_wsgi_app

	def __call__(self, environ, start_response):
		path = environ.get("PATH_INFO", "") or ""
		if path.startswith(RICONFEZIONAMENTO_PREFIX):
			if not os.environ.get("RICONFEZIONAMENTO_ONLINE_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}:
				start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
				return [b"Riconfezionamento online non disponibile."]
			riconfezionamento_environ = environ.copy()
			stripped_path = path[len(RICONFEZIONAMENTO_PREFIX):] or "/"
			riconfezionamento_environ["PATH_INFO"] = stripped_path
			riconfezionamento_environ["SCRIPT_NAME"] = f"{environ.get('SCRIPT_NAME', '')}{RICONFEZIONAMENTO_PREFIX}"
			return self.riconfezionamento_wsgi_app(riconfezionamento_environ, start_response)
		return self.django_app(environ, start_response)


django_application = get_wsgi_application()
riconfezionamento_application = ASGIMiddleware(RiconfezionamentoAccessMiddleware(riconfezionamento_app))

application = PathDispatcher(django_application, riconfezionamento_application)
