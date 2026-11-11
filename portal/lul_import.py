"""Cedolini dal file unico del consulente (LUL): un PDF con tutti i cedolini del mese.

Ogni pagina riporta il codice fiscale del dipendente e il mese retribuito. Le pagine con lo stesso
codice fiscale formano un cedolino. L'abbinamento al dipendente avviene SOLO sul codice fiscale
(con carattere di controllo valido): niente tentativi sul nome. Ciò che non è certo resta fuori
e viene segnalato.
"""
import io
import logging
import re
import uuid

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import redirect, render

logger = logging.getLogger(__name__)

MONTHS = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre',
          'ottobre', 'novembre', 'dicembre']
MAX_PDF_BYTES = 40 * 1024 * 1024
SESSION_KEY = 'lul_import'

# ---------------------------------------------------------------- codice fiscale
_OMO = dict(zip('LMNPQRSTUV', '0123456789'))
_ODD = {**dict(zip('0123456789', (1, 0, 5, 7, 9, 13, 15, 17, 19, 21))),
        **dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ', (1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8, 12,
                                                    14, 16, 10, 22, 25, 24, 23)))}
_EVEN = {**{str(i): i for i in range(10)}, **{c: i for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}}
_CF_SHAPE = re.compile(r'^[A-Z]{6}[0-9LMNPQRSTUV]{2}[ABCDEHLMPRST][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]$')


def valid_cf(cf):
    """Vero se è un codice fiscale di persona con carattere di controllo corretto (omocodie comprese)."""
    cf = (cf or '').strip().upper()
    if not _CF_SHAPE.match(cf):
        return False
    total = sum(_ODD[c] if i % 2 == 0 else _EVEN[c] for i, c in enumerate(cf[:15]))
    return 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[total % 26] == cf[15]


def _norm_name(text):
    import unicodedata
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode()
    return ' '.join(sorted(re.sub(r"[^A-Za-z ]", ' ', text.replace("'", '')).upper().split()))


# ---------------------------------------------------------------- lettura del PDF
def _page_info(page):
    """(codice fiscale | None, nome scritto sul cedolino, mese, anno, problema | None) di una pagina."""
    words = page.get_text('words')
    cfs = sorted({w[4].upper() for w in words if len(w[4]) == 16 and valid_cf(w[4])})
    period = None
    name = ''
    for w in words:
        if w[4].lower() in MONTHS:
            row = sorted((x for x in words if abs(x[1] - w[1]) < 3), key=lambda x: x[0])
            idx = row.index(w)
            if idx + 1 < len(row) and re.fullmatch(r'20\d\d', row[idx + 1][4]):
                period = (MONTHS.index(w[4].lower()) + 1, int(row[idx + 1][4]))
                label = next((x for x in words if x[4] == 'COGNOME' and x[1] < w[1]), None)
                if label:
                    parts = []
                    for x in row:
                        if x[0] < label[0] - 2:
                            continue
                        if re.search(r'\d', x[4]):
                            break
                        parts.append(x[4])
                    name = ' '.join(parts)
                break
    problem = None
    if len(cfs) != 1:
        problem = 'codice fiscale non trovato' if not cfs else 'più codici fiscali nella stessa pagina'
    elif not period:
        problem = 'mese retribuito non trovato'
    return (cfs[0] if len(cfs) == 1 else None), name, (period[0] if period else None), (period[1] if period else None), problem


def analyze(data):
    """PDF del consulente -> {'pages': n, 'groups': [...], 'loose': [...]}.

    groups: un elemento per codice fiscale: {'cf', 'name', 'pages': [1-based], 'month', 'year', 'problem'}
    loose: pagine non attribuibili: {'page', 'problem'}
    """
    import fitz
    doc = fitz.open(stream=data, filetype='pdf')
    groups, loose = {}, []
    for number, page in enumerate(doc, start=1):
        cf, name, month, year, problem = _page_info(page)
        if problem:
            loose.append({'page': number, 'problem': problem})
            continue
        g = groups.setdefault(cf, {'cf': cf, 'name': name, 'pages': [], 'month': month, 'year': year, 'problem': None})
        g['pages'].append(number)
        if (g['month'], g['year']) != (month, year):
            g['problem'] = 'le pagine riportano mesi diversi'
        if name and not g['name']:
            g['name'] = name
    return {'pages': len(doc), 'groups': list(groups.values()), 'loose': loose}


def extract_pdf(data, pages):
    """Nuovo PDF con le sole pagine indicate (numeri da 1)."""
    import fitz
    src = fitz.open(stream=data, filetype='pdf')
    out = fitz.open()
    for n in pages:
        out.insert_pdf(src, from_page=n - 1, to_page=n - 1)
    buf = io.BytesIO()
    out.save(buf, garbage=3, deflate=True)
    return buf.getvalue()


# ---------------------------------------------------------------- abbinamento
def build_rows(analysis):
    """Per ogni cedolino: dipendente certo (stesso codice fiscale) oppure proposta da confermare."""
    from .models import Employee, Payslip
    employees = list(Employee.objects.select_related('user').order_by('last_name', 'first_name'))
    by_cf = {}
    for e in employees:
        if e.fiscal_code:
            by_cf.setdefault(e.fiscal_code.upper(), []).append(e)
    by_name = {}
    for e in employees:
        key = _norm_name(f'{e.last_name or ""} {e.first_name or ""}')
        if key:
            by_name.setdefault(key, []).append(e)
    rows = []
    for g in analysis['groups']:
        row = dict(g, employee=None, proposal=None, status='', note='', exists=False)
        holders = by_cf.get(g['cf'], [])
        if g['problem']:
            row['status'], row['note'] = 'blocked', g['problem']
        elif len(holders) == 1:
            row['employee'], row['status'] = holders[0], 'sure'
        elif len(holders) > 1:
            row['status'], row['note'] = 'blocked', 'lo stesso codice fiscale è su più dipendenti: correggi le schede'
        else:
            same = [e for e in by_name.get(_norm_name(g['name']), []) if not e.fiscal_code]
            row['status'] = 'confirm'
            if len(same) == 1:
                row['proposal'] = same[0]
                row['note'] = 'codice fiscale non ancora registrato: stesso cognome e nome, conferma tu'
            else:
                row['note'] = 'codice fiscale non registrato: scegli tu il dipendente oppure lascia fuori'
        target = row['employee']
        if target and g['month'] and Payslip.objects.filter(employee=target, year=g['year'], month=g['month']).exists():
            row['exists'] = True
        rows.append(row)
    rows.sort(key=lambda r: ({'blocked': 0, 'confirm': 1, 'sure': 2}[r['status']], r['name']))
    return rows, employees


def _storage():
    from .views import _get_pending_import_storage
    return _get_pending_import_storage()


@login_required
def admin_lul_import(request):
    from .models import Employee, Payslip
    from .push import notify_payslip
    from .views import _create_audit_event
    if not request.user.is_staff:
        return redirect('dashboard')
    storage = _storage()
    ctx = {'error': None, 'rows': None, 'done': None}
    state = request.session.get(SESSION_KEY)

    def load():
        if not state or not storage.exists(state['path']):
            return None
        with storage.open(state['path'], 'rb') as fh:
            return fh.read()

    def clear():
        if state:
            try:
                storage.delete(state['path'])
            except Exception:
                logger.exception('lul: file temporaneo non eliminato')
        request.session.pop(SESSION_KEY, None)

    action = request.POST.get('action') if request.method == 'POST' else None
    if action == 'cancel':
        clear()
        return redirect('admin_lul_import')

    if action == 'upload':
        upload = request.FILES.get('pdf')
        if not upload:
            ctx['error'] = 'Scegli il file PDF del consulente.'
        elif upload.size > MAX_PDF_BYTES:
            ctx['error'] = 'File troppo grande.'
        else:
            data = upload.read()
            try:
                analysis = analyze(data)
            except Exception:
                logger.exception('lul: PDF non leggibile')
                analysis = None
            if not analysis or not (analysis['groups'] or analysis['loose']):
                ctx['error'] = 'Non riesco a leggere questo file: deve essere il PDF dei cedolini inviato dal consulente.'
            else:
                clear()
                path = storage.save(f'lul-{uuid.uuid4().hex}.pdf', ContentFile(data))
                request.session[SESSION_KEY] = {'path': path, 'name': upload.name[:120]}
                return redirect('admin_lul_import')

    data = load()
    if state and data is None:
        request.session.pop(SESSION_KEY, None)
        ctx['error'] = 'Il file caricato non è più disponibile: caricalo di nuovo.'
        state = None
    if data is not None:
        analysis = analyze(data)
        rows, employees = build_rows(analysis)

        if action == 'confirm':
            chosen, errors = [], []
            used = {}
            for r in rows:
                if r['status'] == 'blocked' or request.POST.get(f'skip_{r["cf"]}') == '1':
                    continue
                if r['status'] == 'sure':
                    emp = r['employee']
                else:
                    emp_id = request.POST.get(f'emp_{r["cf"]}') or ''
                    if not emp_id.isdigit():
                        continue  # lasciato fuori
                    emp = next((e for e in employees if e.id == int(emp_id)), None)
                    if emp is None:
                        continue
                    if emp.fiscal_code and emp.fiscal_code.upper() != r['cf']:
                        errors.append(f'{emp.full_name} ha già un altro codice fiscale registrato: cedolino di «{r["name"]}» lasciato fuori.')
                        continue
                if emp.id in used:
                    errors.append(f'{emp.full_name} è stato scelto per due cedolini diversi («{used[emp.id]}» e «{r["name"]}»): lasciati fuori entrambi.')
                    chosen = [c for c in chosen if c[1].id != emp.id]
                    continue
                used[emp.id] = r['name']
                chosen.append((r, emp))
            saved = skipped_existing = 0
            for r, emp in chosen:
                replace = request.POST.get(f'replace_{r["cf"]}') == '1'
                with transaction.atomic():
                    existing = Payslip.objects.filter(employee=emp, year=r['year'], month=r['month']).first()
                    if existing and not replace:
                        skipped_existing += 1
                        continue
                    if r['status'] == 'confirm' and not emp.fiscal_code:
                        emp.fiscal_code = r['cf']
                        emp.save(update_fields=['fiscal_code'])
                    if existing:
                        try:
                            existing.pdf.delete(save=False)
                        except Exception:
                            logger.exception('lul: vecchio cedolino non eliminato')
                        existing.delete()
                    payslip = Payslip(employee=emp, year=r['year'], month=r['month'])
                    fname = re.sub(r'[^A-Za-z0-9_]+', '_', f'{emp.last_name or ""}_{emp.first_name or ""}').strip('_') or f'dipendente_{emp.id}'
                    payslip.pdf.save(f'{fname}_{MONTHS[r["month"] - 1]}_{r["year"]}.pdf', ContentFile(extract_pdf(data, r['pages'])), save=True)
                    notify_payslip(payslip)
                    saved += 1
            _create_audit_event(request, 'payslips_imported_from_lul', metadata={
                'file': state.get('name'), 'saved': saved, 'already_present': skipped_existing,
                'left_out': len(rows) - saved - skipped_existing, 'loose_pages': [p['page'] for p in analysis['loose']]})
            clear()
            ctx['done'] = {'saved': saved, 'existing': skipped_existing, 'left_out': len(rows) - saved - skipped_existing,
                           'errors': errors, 'loose': analysis['loose']}
            return render(request, 'portal/admin_lul_import.html', ctx)

        periods = sorted({(r['year'], r['month']) for r in rows if r['month']})
        ctx.update({
            'rows': rows, 'employees': employees, 'loose': analysis['loose'], 'pages': analysis['pages'],
            'file_name': state.get('name'),
            'period_label': ', '.join(f'{MONTHS[m - 1]} {y}' for y, m in periods),
            'counts': {k: sum(1 for r in rows if r['status'] == k) for k in ('sure', 'confirm', 'blocked')},
        })
    return render(request, 'portal/admin_lul_import.html', ctx)
