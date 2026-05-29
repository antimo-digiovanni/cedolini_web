import os
from http.cookies import SimpleCookie
from urllib.parse import quote

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.conf import settings
from asgiref.sync import sync_to_async
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, load_backend
from django.contrib.sessions.backends.db import SessionStore
from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Mount

django_application = get_asgi_application()

from django.urls import reverse
from portal.access import user_has_riconfezionamento_access
from riconfezionamento_app.main import app as riconfezionamento_app


def _scope_cookie_value(scope, key):
	headers = dict(scope.get('headers') or [])
	cookie_header = headers.get(b'cookie', b'').decode('latin1')
	if not cookie_header:
		return None
	cookies = SimpleCookie()
	cookies.load(cookie_header)
	morsel = cookies.get(key)
	if morsel is None:
		return None
	return morsel.value


def _riconfezionamento_user_from_scope(scope):
	session_key = _scope_cookie_value(scope, settings.SESSION_COOKIE_NAME)
	if not session_key:
		return None

	session = SessionStore(session_key=session_key)
	user_id = session.get(SESSION_KEY)
	backend_path = session.get(BACKEND_SESSION_KEY)
	if not user_id or not backend_path:
		return None

	user = load_backend(backend_path).get_user(user_id)
	if user is None:
		return None

	session_hash = session.get(HASH_SESSION_KEY)
	if session_hash and session_hash != user.get_session_auth_hash():
		return None
	return user


class RiconfezionamentoAccessMiddleware:
	def __init__(self, app):
		self.app = app

	async def __call__(self, scope, receive, send):
		root_path = str(scope.get('root_path') or '')
		path = str(scope.get('path') or '')
		request_path = path if root_path and path.startswith(root_path) else f"{root_path}{path}"
		if scope.get('type') != 'http' or not str(request_path).startswith('/riconfezionamento'):
			return await self.app(scope, receive, send)

		user = await sync_to_async(_riconfezionamento_user_from_scope, thread_sensitive=True)(scope)
		has_access = bool(user) and await sync_to_async(user_has_riconfezionamento_access, thread_sensitive=True)(user)
		if user is None or not has_access:
			if user is None:
				query_string = (scope.get('query_string') or b'').decode('latin1')
				next_path = str(request_path or '/riconfezionamento/')
				if query_string:
					next_path = f'{next_path}?{query_string}'
				login_url = reverse('login')
				response = RedirectResponse(url=f'{login_url}?next={quote(next_path, safe="")}', status_code=302)
				return await response(scope, receive, send)

			response = PlainTextResponse('Riconfezionamento non disponibile per questo account.', status_code=403)
			return await response(scope, receive, send)

		return await self.app(scope, receive, send)

application = Starlette(
	routes=[
		Mount('/riconfezionamento', app=RiconfezionamentoAccessMiddleware(riconfezionamento_app)),
		Mount('/', app=django_application),
	]
)
