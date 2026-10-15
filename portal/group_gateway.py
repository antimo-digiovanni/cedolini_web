import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/javascript', '.js')

GROUP_ASSETS = {
    'app.js', 'style.css',
    'assets/fonts.css', 'assets/gsap.min.js', 'assets/ScrollTrigger.min.js',
    'assets/lenis.min.js',
    'assets/instrument-serif-latin-400-normal.woff2',
    'assets/instrument-serif-latin-400-italic.woff2',
    'assets/inter-tight-latin-wght-normal.woff2',
    'assets/antimo-petroli.png', 'assets/catering.png', 'assets/eurofrozen.png',
    'assets/flotta.png', 'assets/gruppo-hero.png',
    'assets/gruppo-servizi-hero.png', 'assets/logo-gruppo.svg',
    'assets/san-vincenzo-servizi.png', 'assets/san-vincenzo.png',
    'assets/timmy.png',
}


@require_safe
def group_home(request):
    content = (Path(settings.BASE_DIR) / 'gruppo-di-giovanni' / 'index.html').read_text(encoding='utf-8')
    return HttpResponse(content)


@require_safe
def group_asset(request, filename):
    if filename not in GROUP_ASSETS:
        raise Http404
    return FileResponse((Path(settings.BASE_DIR) / 'gruppo-di-giovanni' / filename).open('rb'))


@never_cache
@require_safe
def select_san_vincenzo(request):
    return redirect('public_home')