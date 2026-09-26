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

HOME_PRELOADER_STYLE = '''
<style>
body.sv-page-loading{overflow:hidden}
.sv-preloader{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;background:#071e32;color:#fff;opacity:1;visibility:visible;transition:opacity .8s ease,visibility .8s ease}
.sv-preloader.is-done{opacity:0;visibility:hidden;pointer-events:none}
.sv-preloader-inner{width:min(360px,100vw);text-align:center;padding:0 16px}
.sv-preloader-mark{width:86px;height:86px;margin:0 auto 23px;object-fit:contain;animation:sv-preloader-breathe 2.4s ease-in-out infinite}
.sv-preloader-brand{font:600 clamp(25px,7vw,40px)/1.1 Manrope,sans-serif;white-space:nowrap;animation:sv-preloader-breathe 2.4s ease-in-out infinite}
.sv-preloader-label{margin-top:11px;color:#bed2df;font:500 11px/1.4 'DM Sans',sans-serif;letter-spacing:.19em;text-transform:uppercase}
.sv-preloader-track{height:2px;margin:25px auto 0;overflow:hidden;background:#ffffff30}
.sv-preloader-track span{display:block;width:100%;height:100%;transform-origin:left;background:linear-gradient(90deg,#124e75,#ff7b40,#124e75);animation:sv-preloader-line 1.8s ease-in-out infinite}
@keyframes sv-preloader-breathe{0%,100%{opacity:.72;transform:scale(.985)}50%{opacity:1;transform:scale(1.015)}}
@keyframes sv-preloader-line{0%,100%{transform:scaleX(.28);opacity:.55}50%{transform:scaleX(1);opacity:1}}
@media(prefers-reduced-motion:reduce){.sv-preloader-mark,.sv-preloader-brand,.sv-preloader-track span{animation:none}}
</style>
'''

HOME_PRELOADER_MARKUP = '''
<div class="sv-preloader" id="sv-preloader" role="status" aria-live="polite">
    <div class="sv-preloader-inner">
        <img class="sv-preloader-mark" src="/san-vincenzo-assets/logo.8ca8c200bab7.webp" alt="">
        <div class="sv-preloader-brand">San Vincenzo</div>
        <div class="sv-preloader-label" id="sv-preloader-label">Azienda multiservizi</div>
        <div class="sv-preloader-track" aria-hidden="true"><span></span></div>
    </div>
</div>
<noscript><style>.sv-preloader{display:none}body.sv-page-loading{overflow:auto}</style></noscript>
'''


def _add_home_preloader(content, preview=False):
        html = content.decode('utf-8')
        html = html.replace('</head>', HOME_PRELOADER_STYLE + '</head>', 1)
        html = html.replace(
                '<body class="page-sito-web">',
                '<body class="page-sito-web sv-page-loading">' + HOME_PRELOADER_MARKUP,
                1,
        )
        preview_value = 'true' if preview else 'false'
        preloader_script = f'''<script>
(() => {{
    const overlay = document.getElementById('sv-preloader');
    if (!overlay) return;
    const startedAt = performance.now();
    const preview = {preview_value};
    if (preview) {{
        document.getElementById('sv-preloader-label').textContent = 'Anteprima';
        return;
    }}
    let released = false;
    const reveal = () => {{
        if (released) return;
        released = true;
        const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
        const minimum = reducedMotion ? 0 : 1800;
        setTimeout(() => {{
            document.body.classList.remove('sv-page-loading');
            overlay.classList.add('is-done');
        }}, Math.max(0, minimum - (performance.now() - startedAt)));
    }};
    if (document.readyState === 'complete') reveal();
    else addEventListener('load', reveal, {{ once: true }});
    setTimeout(reveal, 5000);
}})();
</script>'''
        html = html.replace('</body>', preloader_script + '</body>', 1)
        return html.encode('utf-8')

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
    content = _read(page + '.html')
    if page == 'index':
        content = _add_home_preloader(
            content,
            preview=request.GET.get('preview-loader') == '1',
        )
    response=HttpResponse(content,content_type='text/html; charset=utf-8')
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
