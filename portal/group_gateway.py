from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


GROUP_ASSETS = {
    'logo-gruppo.svg', 'logo-eurofrozen.png', 'logo-antimo-petroli.png',
    'logo-timmy-gel.png',
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