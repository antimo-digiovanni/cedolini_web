"""Carta aziendale organizzata per giri di ricarica.

Un giro parte dall'ultima ricarica del datore: quanto c'era, quanto è stato speso da allora, quanto resta,
cosa c'è da comprare e quindi quanto chiedere con la prossima ricarica.
"""
import io
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone

MONTHS = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre',
          'ottobre', 'novembre', 'dicembre']
ZERO = Decimal('0.00')


def _euro(v):
    s = f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'{s} €'


def _long_date(d):
    return f'{d.day} {MONTHS[d.month - 1]}'


def current_cycle(user):
    from .models import CorporateCardEntry, PlannedCorporateCardExpense
    entries = CorporateCardEntry.objects.filter(user=user)
    balance = entries.aggregate(t=Sum('balance_delta'))['t'] or ZERO
    top = entries.filter(operation_type=CorporateCardEntry.TYPE_TOP_UP).order_by('-occurred_on', '-created_at', '-id').first()
    spent_qs = entries.exclude(operation_type=CorporateCardEntry.TYPE_TOP_UP)
    if top:
        spent_qs = spent_qs.filter(Q(occurred_on__gt=top.occurred_on) | Q(occurred_on=top.occurred_on, created_at__gte=top.created_at))
    expenses = list(spent_qs.order_by('-occurred_on', '-created_at', '-id'))
    spent = sum((e.amount for e in expenses), ZERO)
    planned = list(PlannedCorporateCardExpense.objects.filter(user=user, paid_entry__isnull=True).order_by('planned_on', 'id'))
    planned_total = sum((p.amount for p in planned), ZERO)
    available = spent + balance  # quanto c'era sulla carta all'inizio del giro (ricarica + avanzo)
    pct = int(round(min(100, max(0, float(spent / available * 100))))) if available > 0 else 0
    return {
        'top': top,
        'top_label': f'Ricarica del {_long_date(top.occurred_on)} · {_euro(top.amount)}' if top else 'Nessuna ricarica registrata',
        'balance': balance,
        'spent': spent,
        'available': available,
        'carry_over': available - (top.amount if top else ZERO),
        'pct_spent': pct,
        'expenses': expenses,
        'planned': planned,
        'planned_total': planned_total,
        'request_amount': max(ZERO, planned_total - max(balance, ZERO)),
    }


def _image_bytes(field):
    """Byte PNG/JPG di uno scontrino (anche PDF: prima pagina), oppure None."""
    try:
        field.open('rb')
        data = field.read()
        field.close()
    except Exception:  # noqa: BLE001
        return None
    if (field.name or '').lower().endswith('.pdf'):
        try:
            import fitz
            doc = fitz.open(stream=data, filetype='pdf')
            if not doc.page_count:
                return None
            data = doc.load_page(0).get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False).tobytes('png')
        except Exception:  # noqa: BLE001
            return None
    return data


def request_pdf_response(request):
    """PDF «Richiesta di ricarica»: spese del giro con scontrini, cosa comprare, ricarica richiesta."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    user = request.user
    c = current_cycle(user)
    emp = getattr(user, 'employee', None)
    name = (emp.full_name if emp else '') or user.get_full_name() or user.get_username()
    today = timezone.localdate()

    ss = getSampleStyleSheet()
    ink = colors.HexColor('#1C2742')
    muted = colors.HexColor('#65708A')
    st = {
        'h': ParagraphStyle('h', parent=ss['Heading2'], fontSize=12.5, leading=16, textColor=ink, spaceBefore=10, spaceAfter=4),
        'c': ParagraphStyle('c', parent=ss['BodyText'], fontSize=9.5, leading=12, textColor=ink),
        'r': ParagraphStyle('r', parent=ss['BodyText'], fontSize=9.5, leading=12, textColor=ink, alignment=2),
        'm': ParagraphStyle('m', parent=ss['BodyText'], fontSize=8.5, leading=11, textColor=muted),
        'big': ParagraphStyle('big', parent=ss['BodyText'], fontSize=20, leading=24, textColor=ink, alignment=2),
    }
    logo = Path(settings.BASE_DIR) / 'portal' / 'static' / 'portal' / 'logo.png'

    def header(canvas, doc):
        canvas.saveState()
        top = A4[1] - 16 * mm
        if logo.exists():
            canvas.drawImage(str(logo), 18 * mm, top - 13 * mm, width=14 * mm, height=14 * mm, preserveAspectRatio=True, mask='auto')
        canvas.setFillColor(ink)
        canvas.setFont('Helvetica-Bold', 13)
        canvas.drawString(36 * mm, top - 5 * mm, 'Richiesta di ricarica carta aziendale')
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(muted)
        canvas.drawString(36 * mm, top - 10.5 * mm, f'{name} · {today.day} {MONTHS[today.month - 1]} {today.year}')
        canvas.setStrokeColor(ink)
        canvas.setLineWidth(1.2)
        canvas.line(18 * mm, top - 16 * mm, A4[0] - 18 * mm, top - 16 * mm)
        canvas.setFont('Helvetica', 7.5)
        canvas.drawCentredString(A4[0] / 2, 10 * mm, f'Pagina {doc.page}')
        canvas.restoreState()

    def table(rows, widths, total_row=True):
        t = Table(rows, colWidths=widths, repeatRows=1)
        style = [
            ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#DDE2EA')),
            ('TEXTCOLOR', (0, 0), (-1, 0), muted),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]
        if total_row:
            style += [('LINEABOVE', (0, -1), (-1, -1), 1, ink), ('LINEBELOW', (0, -1), (-1, -1), 0, colors.white)]
        t.setStyle(TableStyle(style))
        return t

    story = []
    if c['top']:
        intro = f"1. Spese fatte con la ricarica del {c['top'].occurred_on:%d/%m/%Y} ({_euro(c['top'].amount)})"
    else:
        intro = '1. Spese fatte'
    story.append(Paragraph(intro, st['h']))
    if c['carry_over'] > 0 and c['top']:
        story.append(Paragraph(f"Sulla carta c'erano anche {_euro(c['carry_over'])} avanzati dal giro precedente.", st['m']))
    if c['expenses']:
        rows = [[Paragraph('<b>Data</b>', st['m']), Paragraph('<b>Cosa</b>', st['m']), Paragraph('<b>Scontrino</b>', st['m']), Paragraph('<b>Importo</b>', st['m'])]]
        for e in sorted(c['expenses'], key=lambda e: (e.occurred_on, e.created_at)):
            what = e.category + (f' – {e.description}' if e.description else '')
            if e.operation_type == 'withdrawal':
                what = 'Prelievo contanti' + (f' – {e.cash_delivery_note}' if e.cash_delivery_note else '') + (f' ({e.category})' if e.category else '')
            rows.append([Paragraph(e.occurred_on.strftime('%d/%m/%Y'), st['c']), Paragraph(what, st['c']),
                         Paragraph('sì' if e.receipt_image else '—', st['c']), Paragraph(_euro(e.amount), st['r'])])
        rows.append(['', Paragraph(f"<b>Totale speso</b> · restano sulla carta <b>{_euro(c['balance'])}</b>", st['c']), '',
                     Paragraph(f"<b>{_euro(c['spent'])}</b>", st['r'])])
        story.append(table(rows, [24 * mm, 104 * mm, 20 * mm, 26 * mm]))
    else:
        story.append(Paragraph('Nessuna spesa registrata dall\'ultima ricarica.', st['c']))

    story.append(Paragraph('2. Da comprare', st['h']))
    if c['planned']:
        rows = [[Paragraph('<b>Cosa</b>', st['m']), Paragraph('<b>Importo previsto</b>', st['m'])]]
        for p in c['planned']:
            rows.append([Paragraph(p.category + (f' – {p.description}' if p.description else ''), st['c']), Paragraph(_euro(p.amount), st['r'])])
        rows.append([Paragraph('<b>Totale da comprare</b>', st['c']), Paragraph(f"<b>{_euro(c['planned_total'])}</b>", st['r'])])
        story.append(table(rows, [138 * mm, 36 * mm]))
    else:
        story.append(Paragraph('Nessun acquisto in lista.', st['c']))

    ask = Table([[Paragraph('<b>Ricarica richiesta</b>', st['c']), Paragraph(f"<b>{_euro(c['request_amount'])}</b>", st['big'])]],
                colWidths=[100 * mm, 74 * mm])
    ask.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EEF2FB')), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                             ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                             ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10)]))
    story += [Spacer(1, 8 * mm), ask, Spacer(1, 2 * mm),
              Paragraph(f"{_euro(c['planned_total'])} da comprare − {_euro(max(c['balance'], ZERO))} ancora sulla carta.", st['m'])]

    receipts = [(e.occurred_on, e.category, e.amount, e.receipt_image) for e in sorted(c['expenses'], key=lambda e: e.occurred_on) if e.receipt_image]
    receipts += [(p.planned_on, f'{p.category} (preventivo)', p.amount, p.receipt_image) for p in c['planned'] if p.receipt_image]
    blocks = []
    for d, label, amount, field in receipts:
        data = _image_bytes(field)
        if not data:
            continue
        try:
            w, h = ImageReader(io.BytesIO(data)).getSize()
        except Exception:  # noqa: BLE001
            continue
        k = min(80 * mm / w, 105 * mm / h, 1)
        blocks.append(KeepTogether([Paragraph(f'{d:%d/%m/%Y} · {label} · {_euro(amount)}', st['m']),
                                    RLImage(io.BytesIO(data), width=w * k, height=h * k), Spacer(1, 5 * mm)]))
    if blocks:
        story += [PageBreak(), Paragraph('Scontrini', st['h'])] + blocks

    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=38 * mm, bottomMargin=16 * mm,
                            title='Richiesta di ricarica carta aziendale', author=name)
    doc.build(story, onFirstPage=header, onLaterPages=header)
    resp = HttpResponse(out.getvalue(), content_type='application/pdf')
    disp = 'attachment' if request.GET.get('scarica') == '1' else 'inline'
    resp['Content-Disposition'] = f'{disp}; filename="richiesta-ricarica-{today:%Y-%m-%d}.pdf"'
    return resp
