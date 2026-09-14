"""Public brochure pages only; employee views and authentication stay unchanged."""
import mimetypes
import re
from pathlib import Path
from zipfile import ZipFile

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_safe

PAGES = {'index', 'chi-siamo', 'servizi', 'servizi-digitali',
         'disinfestazione-derattizzazione', 'macchinari', 'contatti'}

def _read(name):
    with ZipFile(Path(settings.BASE_DIR) / 'san-vincenzo-public.zip') as archive:
        try:
            return archive.read(name)
        except KeyError:
            raise Http404

def home(request):
    if request.user.is_authenticated:
        from .views import home as employee_home
        return employee_home(request)
    return page(request, 'index')

def page(request, page='index'):
    if page not in PAGES:
        raise Http404
    if request.method == 'POST' and page == 'contatti':
        from .views import public_contacts
        return public_contacts(request)
    if request.method not in ('GET', 'HEAD'):
        return HttpResponse(status=405)
    response=HttpResponse(_read(page+'.html'),content_type='text/html; charset=utf-8')
    response['Cache-Control']='no-cache'
    return response

@require_safe
def asset(request, filename):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',filename):
        raise Http404
    data=_read('assets/'+filename)
    total=len(data)
    content_type=mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    status=200; start=0; end=total-1
    requested=request.headers.get('Range')
    if requested:
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
        if not match or not any(match.groups()):
            response=HttpResponse(status=416);response['Content-Range']=f'bytes */{total}';return response
        first,last=match.groups()
        if first:
            start=int(first);end=min(int(last),end) if last else end
        else:start=max(0,total-int(last))
        if start>end or start>=total:
            response=HttpResponse(status=416);response['Content-Range']=f'bytes */{total}';return response
        status=206
    response=HttpResponse(data[start:end+1] if request.method!='HEAD' else b'',status=status,content_type=content_type)
    response['Content-Length']=str(end-start+1)
    response['Accept-Ranges']='bytes'
    response['Cache-Control']='public, max-age=3600'
    response['X-Content-Type-Options']='nosniff'
    if status==206:response['Content-Range']=f'bytes {start}-{end}/{total}'
    return response
