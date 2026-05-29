"""WSGI entrypoint.

Render may still boot the project through ``config.wsgi:application`` even when
the service should really run the ASGI stack. Wrapping the ASGI application here
keeps ``/riconfezionamento/`` available in both deployment modes.
"""

import os

from a2wsgi import ASGIMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from config.asgi import application as asgi_application


application = ASGIMiddleware(asgi_application)
