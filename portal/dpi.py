"""Modulo di consegna DPI (D.Lgs. 81/2008): generazione del PDF firmato."""

import base64
import io
from pathlib import Path

from PIL import Image
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

COMPANY_NAME = 'SAN VINCENZO S.R.L.'
COMPANY_ADDRESS = 'VIA B. CELLINI 154 GRUMO NEVANO (NAPOLI)'
DELIVERY_PLACE = 'CAIVANO'

# (chiave, etichetta, ha_quantita)
STANDARD_ITEMS = [
    ('guanti', 'Guanti anti-taglio', False),
    ('scarpe', 'Scarpe di sicurezza', False),
    ('alta_visibilita', 'Indumenti ad alta visibilità', False),
    ('pantaloni', 'Pantaloni', True),
    ('tshirt', 'T-shirt', True),
    ('giacche', 'Giacche', True),
]

MAX_SIGNATURE_BYTES = 1500 * 1024
COMPANY_STAMP_PATH = Path(__file__).resolve().parent / 'dpi_assets' / 'timbro_firma_azienda.png'

INFORMATIVA = [
    ('Articolo 20 D.Lgs. 81/2008 - Obbligo di uso', [
        '1. Ogni lavoratore deve prendersi cura della propria salute e sicurezza e di quella delle altre persone presenti sul luogo di lavoro, su cui ricadono gli effetti delle sue azioni o omissioni, conformemente alla sua formazione, alle istruzioni e ai mezzi forniti dal datore di lavoro.',
        '2. I lavoratori devono in particolare:',
        'a) contribuire, insieme al datore di lavoro, ai dirigenti e ai preposti, all\'adempimento degli obblighi previsti a tutela della salute e sicurezza sui luoghi di lavoro;',
        'b) osservare le disposizioni e le istruzioni impartite dal datore di lavoro, dai dirigenti e dai preposti, ai fini della protezione collettiva ed individuale;',
        'c) utilizzare correttamente le attrezzature di lavoro, le sostanze e i preparati pericolosi, i mezzi di trasporto e, nonché i dispositivi di sicurezza;',
        'd) utilizzare in modo appropriato i dispositivi di protezione messi a loro disposizione;',
        'e) segnalare immediatamente al datore di lavoro, al dirigente o al preposto le deficienze dei mezzi e dei dispositivi di cui alle lettere c) e d), nonché qualsiasi eventuale condizione di pericolo di cui vengano a conoscenza, adoperandosi direttamente, in caso di urgenza, nell\'ambito delle proprie competenze e possibilità e fatto salvo l\'obbligo di cui alla lettera f) per eliminare o ridurre le situazioni di pericolo grave e incombente, dandone notizia al rappresentante dei lavoratori per la sicurezza;',
        'f) non rimuovere o modificare senza autorizzazione i dispositivi di sicurezza o di segnalazione o di controllo;',
        'g) non compiere di propria iniziativa operazioni o manovre che non sono di loro competenza ovvero che possono compromettere la sicurezza propria o di altri lavoratori;',
        'h) partecipare ai programmi di formazione e di addestramento organizzati dal datore di lavoro;',
        'i) sottoporsi ai controlli sanitari previsti dal presente decreto legislativo o comunque disposti dal medico competente.',
        '3. I lavoratori di aziende che svolgono attività in regime di appalto o subappalto, devono esporre apposita tessera di riconoscimento, corredata di fotografia, contenente le generalità del lavoratore e l\'indicazione del datore di lavoro. Tale obbligo grava anche in capo ai lavoratori autonomi che esercitano direttamente la propria attività nel medesimo luogo di lavoro, i quali sono tenuti a provvedervi per proprio conto.',
    ]),
    ('Articolo 59 - Sanzioni per i lavoratori', [
        '1. I lavoratori sono puniti:',
        'a) con l\'arresto fino a un mese o con l\'ammenda da 200 a 600 euro per la violazione degli articoli 20, comma 2, lettere b), c), d), e), f), g), h) e i), e 43, comma 3, primo periodo;',
        'b) con la sanzione amministrativa pecuniaria da 50 a 300 euro per la violazione dell\'articolo 20 comma 3.',
    ]),
    ('Articolo 75 D.Lgs. 81/2008 - Obbligo di uso', [
        'I DPI devono essere impiegati quando i rischi non possono essere evitati o sufficientemente ridotti da misure tecniche di prevenzione, da mezzi di protezione collettiva, da misure, metodi o procedimenti di riorganizzazione del lavoro.',
    ]),
    ('Articolo 78 D.Lgs. 81/2008 - Obblighi dei lavoratori', [
        '1. In ottemperanza a quanto previsto dall\'articolo 20, comma 2, lettera h), i lavoratori si sottopongono al programma di formazione e addestramento organizzato dal datore di lavoro nei casi ritenuti necessari ai sensi dell\'articolo 77 commi 4, lettera h), e 5.',
        '2. In ottemperanza a quanto previsto dall\'articolo 20, comma 2, lettera d), i lavoratori utilizzano i DPI messi a loro disposizione conformemente all\'informazione e alla formazione ricevute e all\'addestramento eventualmente organizzato ed espletato.',
        '3. I lavoratori:',
        'a) provvedono alla cura dei DPI messi a loro disposizione;',
        'b) non vi apportano modifiche di propria iniziativa.',
        '4. Al termine dell\'utilizzo i lavoratori seguono le procedure aziendali in materia di riconsegna dei DPI.',
        '5. I lavoratori segnalano immediatamente al datore di lavoro o al dirigente o al preposto qualsiasi difetto o inconveniente da essi rilevato nei DPI messi a loro disposizione.',
    ]),
]


class DpiError(ValueError):
    pass


def decode_signature(data_url):
    """Valida un data URL PNG e restituisce i byte dell'immagine (sfondo bianco)."""
    prefix = 'data:image/png;base64,'
    if not data_url or not data_url.startswith(prefix):
        raise DpiError('Firma mancante.')
    try:
        raw = base64.b64decode(data_url[len(prefix):], validate=True)
    except Exception:
        raise DpiError('Firma non valida.')
    if not raw or len(raw) > MAX_SIGNATURE_BYTES:
        raise DpiError('Firma non valida.')
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
        img = img.convert('RGBA')
    except Exception:
        raise DpiError('Firma non valida.')
    if img.width * img.height > 4_000_000:
        raise DpiError('Firma non valida.')
    background = Image.new('RGBA', img.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(background, img).convert('RGB')
    # Firma vuota: nessun pixel scuro.
    gray = flat.convert('L')
    if gray.getextrema()[0] > 200:
        raise DpiError('Firma mancante.')
    # Ritaglia attorno al tratto così la firma occupa tutto lo spazio nel PDF.
    bbox = gray.point(lambda v: 255 if v < 200 else 0).getbbox()
    if bbox:
        pad = 12
        bbox = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                min(flat.width, bbox[2] + pad), min(flat.height, bbox[3] + pad))
        flat = flat.crop(bbox)
    out = io.BytesIO()
    flat.save(out, format='PNG')
    return out.getvalue()


def item_text(label, qty, has_qty):
    label = (label or '').strip()
    if has_qty:
        return f'n. {qty} {label.lower()}'
    return label


def build_items(post):
    """Ricava l'elenco [{label, qty, text}] dai campi del form."""
    selected = set(post.getlist('item'))
    items = []
    for key, label, has_qty in STANDARD_ITEMS:
        if key not in selected:
            continue
        qty = _parse_qty(post.get(f'qty_{key}')) if has_qty else 1
        items.append({'label': label, 'qty': qty, 'text': item_text(label, qty, has_qty)})
    labels = post.getlist('extra_label')
    qtys = post.getlist('extra_qty')
    for idx, label in enumerate(labels):
        label = (label or '').strip()[:80]
        if not label:
            continue
        qty = _parse_qty(qtys[idx] if idx < len(qtys) else '1')
        items.append({'label': label, 'qty': qty, 'text': item_text(label, qty, True)})
    return items


def _parse_qty(value):
    try:
        qty = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(qty, 99))


def build_pdf(*, employee_name, delivered_on, items, signature_png):
    """Genera il PDF a 2 pagine: modulo di consegna + informativa."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=16 * mm, bottomMargin=12 * mm,
        title=f'Consegna DPI - {employee_name}', author=COMPANY_NAME,
    )
    base = ParagraphStyle('base', fontName='Helvetica', fontSize=10.5, leading=15)
    small = ParagraphStyle('small', parent=base, fontSize=8, leading=10)
    head = ParagraphStyle('head', parent=base, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=15)
    sub = ParagraphStyle('sub', parent=base, alignment=TA_CENTER)
    art = ParagraphStyle('art', parent=small, fontName='Helvetica-Bold', spaceBefore=5, spaceAfter=1)
    cap = ParagraphStyle('cap', parent=base, fontSize=8.5, leading=10)

    date_txt = delivered_on.strftime('%d/%m/%Y')
    sig_img = ImageReader(io.BytesIO(signature_png))
    sig_w, sig_h = sig_img.getSize()
    box_w, box_h = 78 * mm, 34 * mm
    scale = min(box_w / sig_w, box_h / sig_h)

    def sig():
        return RLImage(io.BytesIO(signature_png), width=sig_w * scale, height=sig_h * scale)

    def esc(text):
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    story = [
        Paragraph(f'{COMPANY_NAME}<br/>{COMPANY_ADDRESS}', base),
        Spacer(1, 10 * mm),
        Paragraph('MODULO DI CONSEGNA<br/>DISPOSITIVI DI PROTEZIONE INDIVIDUALE (D.P.I.)', head),
        Paragraph('ai sensi del D.Lgs. 81/2008', sub),
        Spacer(1, 9 * mm),
        Paragraph(
            'Il sottoscritto Vincenzo Di Giovanni in qualità di Datore di Lavoro dell\'Impresa San Vincenzo s.r.l. '
            'con sede in VIA B. CELLINI 154 GRUMO NEVANO (NA) in seguito alla valutazione dei rischi e per le '
            f'attività svolte consegna al Dipendente Sig./Sig.ra <b>{esc(employee_name)}</b> '
            'i seguenti Dispositivi di Protezione Individuale in ottemperanza al Testo Unico Sicurezza e Salute '
            'sul Lavoro di cui al Decreto Legislativo n. 81/2008 ad oggi aggiornato:', base),
        Spacer(1, 6 * mm),
    ]

    standard_labels = [lbl for _, lbl, _ in STANDARD_ITEMS]
    rows = []
    for _key, label, has_qty in STANDARD_ITEMS:
        match = next((i for i in items if i['label'] == label), None)
        rows.append(('X', match['text']) if match else ('', label.lower() if has_qty else label))
    rows += [('X', it['text']) for it in items if it['label'] not in standard_labels]
    table = Table([[m, Paragraph(esc(t), base)] for m, t in rows], colWidths=[7 * mm, 130 * mm])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (0, 0), 0.6, (0, 0, 0)),
        *[('BOX', (0, i), (0, i), 0.6, (0, 0, 0)) for i in range(len(rows))],
        ('LEFTPADDING', (1, 0), (1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    table.hAlign = 'LEFT'
    story += [
        table,
        Spacer(1, 7 * mm),
        Paragraph(
            'Il sottoscritto ha provveduto altresì ad informare il lavoratore sulla necessità di indossare detti '
            'Dispositivi e in merito ai rischi dai quali è protetto, nonché a formarlo sul loro corretto utilizzo, '
            'conservazione e smaltimento.', base),
        Spacer(1, 8 * mm),
        Paragraph(f'{DELIVERY_PLACE}, lì {date_txt}', base),
        Spacer(1, 6 * mm),
    ]

    def stamp():
        if not COMPANY_STAMP_PATH.exists():
            return Spacer(1, box_h)
        reader = ImageReader(str(COMPANY_STAMP_PATH))
        w, h = reader.getSize()
        k = min(70 * mm / w, box_h / h)
        return RLImage(str(COMPANY_STAMP_PATH), width=w * k, height=h * k)

    def signatures(worker_caption):
        left = [stamp(), Paragraph('Timbro e Firma del Datore di Lavoro', cap)]
        right = [sig(), Paragraph(worker_caption, cap)]
        t = Table([[left, right]], colWidths=[82 * mm, 82 * mm])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        return t

    story.append(KeepTogether(signatures('Il Lavoratore per presa consegna')))

    story += [PageBreak(),
              Paragraph(f'{COMPANY_NAME}<br/>{COMPANY_ADDRESS}', base),
              Spacer(1, 3 * mm),
              Paragraph('INFORMATIVA ALLEGATA AL MODULO DI CONSEGNA DEI D.P.I.', ParagraphStyle('t', parent=head, fontSize=10)),
              Paragraph('I dispositivi di protezione vanno usati obbligatoriamente durante lo svolgimento delle mansioni, '
                        'secondo le disposizioni del Decreto Legislativo n. 81/2008 riportati per intero nella presente '
                        'nota informativa', small)]
    for title, paragraphs in INFORMATIVA:
        story.append(Paragraph(esc(title), art))
        for p in paragraphs:
            story.append(Paragraph(esc(p), small))
    story += [
        Spacer(1, 4 * mm),
        Paragraph(f'{DELIVERY_PLACE}, lì {date_txt}', base),
        Spacer(1, 2 * mm),
        KeepTogether(Table([[sig()], [Paragraph('Il Lavoratore per avvenuta informazione', cap)]],
                           colWidths=[82 * mm], hAlign='RIGHT')),
    ]
    doc.build(story)
    return buf.getvalue()
