from datetime import datetime
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BASE_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = BASE_DIR / "generated_pdfs"
ASSETS_DIR = BASE_DIR / "assets"

COMPANY_NAME = "SAN VINCENZO SRL"
COMPANY_TAGLINE = (
    "MANUTENZIONE TECNICA, ELETTRICA E MECCANICA DI IMPIANTI INDUSTRIALI - "
    "LAVORI EDILI - CARPENTERIA E LAVORAZIONE DEL LEGNO - TRASPORTI E FACCHINAGGIO - "
    "SERVIZI DI PULIZIA E GIARDINAGGIO - PEST CONTROL"
)
COMPANY_ADDRESS = "Via B. Cellini, 154 - 80028 Grumo Nevano (NA)"
COMPANY_CONTACTS = (
    "Tel. 0818801972 - P.IVA: 07947101213 - www.sanvincenzoservice.it - "
    "sanvincenzosrl@gmail.com - pasquale.digiovanni@sanvincenzosrl.com"
)
DEFAULT_CLOSING = "Cordiali saluti"
DEFAULT_SIGNATURE = "Pasquale Di Giovanni"
DISCOUNT_NOTE = "n.b. sull'offerta e stato applicato uno sconto del 10%."


def create_quote_pdf(quote_row, item_rows) -> Path:
    PDF_DIR.mkdir(exist_ok=True)
    pdf_path = PDF_DIR / _build_output_filename(quote_row)

    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
    )
    styles = _build_styles()
    story = []

    story.extend(_build_header(styles))
    story.extend(_build_document_title_block(quote_row, styles))
    story.extend(_build_recipient_block(quote_row, styles))
    story.append(Spacer(1, 4 * mm))
    story.append(_build_reference_panel(quote_row, styles))
    story.append(Spacer(1, 4 * mm))

    opening_text = quote_row["opening_text"] or quote_row["description"]
    story.append(Paragraph(_normalize_paragraph(opening_text), styles["body"]))
    story.append(Spacer(1, 4 * mm))

    bullet_lines = _extract_bullet_lines(quote_row, item_rows)
    if bullet_lines:
        story.append(Paragraph("Prestazioni comprese nell'offerta", styles["section"] ))
        story.append(_build_bullet_list(bullet_lines, styles))
        story.append(Spacer(1, 4 * mm))

    if item_rows:
        story.append(Paragraph("Computo metrico estimativo", styles["section"]))
        story.append(_build_items_table(item_rows))
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Quadro economico", styles["section"]))
    story.append(_build_amount_table(quote_row, item_rows))

    if _to_bool(quote_row["include_discount_note"]):
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(_normalize_paragraph(DISCOUNT_NOTE), styles["note"] ))

    story.append(Spacer(1, 8 * mm))
    closing_text = quote_row["closing_text"] or DEFAULT_CLOSING
    story.append(Paragraph(_normalize_paragraph(closing_text), styles["body"]))
    story.append(Spacer(1, 4 * mm))
    story.append(_build_signature_block())

    document.build(story)
    return pdf_path


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "company": ParagraphStyle(
            "company",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#16324f"),
            spaceAfter=3,
        ),
        "tagline": ParagraphStyle(
            "tagline",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.6,
            leading=10.5,
            textColor=colors.HexColor("#2f2f2f"),
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#222222"),
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#444444"),
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#16324f"),
            spaceAfter=4,
            spaceBefore=2,
        ),
        "headline": ParagraphStyle(
            "headline",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#16324f"),
            spaceAfter=2,
        ),
        "subheadline": ParagraphStyle(
            "subheadline",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#50657d"),
            spaceAfter=5,
        ),
        "label": ParagraphStyle(
            "label",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.2,
            leading=12,
            textColor=colors.HexColor("#16324f"),
        ),
        "meta": ParagraphStyle(
            "meta",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=12,
            textColor=colors.HexColor("#24313d"),
        ),
        "note": ParagraphStyle(
            "note",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9.2,
            leading=12,
            textColor=colors.HexColor("#4a4a4a"),
        ),
        "right": ParagraphStyle(
            "right",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#222222"),
        ),
    }


def _build_header(styles):
    logo = _build_logo_image()
    company_block = [
        Paragraph(COMPANY_NAME, styles["company"]),
        Paragraph(_normalize_paragraph(COMPANY_TAGLINE), styles["tagline"]),
        Spacer(1, 1.2 * mm),
        Paragraph(_normalize_paragraph(COMPANY_ADDRESS), styles["small"]),
        Paragraph(_normalize_paragraph(COMPANY_CONTACTS), styles["small"]),
    ]

    if logo is None:
        return company_block + [Spacer(1, 6 * mm)]

    header_table = Table([[logo, company_block]], colWidths=[40 * mm, 125 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [header_table, Spacer(1, 5 * mm)]


def _build_document_title_block(quote_row, styles):
    offer_number = _build_offer_number(quote_row)
    title = _normalize_paragraph(quote_row["title"])
    return [
        Paragraph("OFFERTA ECONOMICA / COMPUTO METRICO", styles["headline"]),
        Paragraph(f"{_normalize_paragraph(offer_number)} - {title}", styles["subheadline"]),
        Spacer(1, 1.5 * mm),
    ]


def _build_recipient_block(quote_row, styles):
    recipient_lines = ["Spett.le", quote_row["client_name"]]
    if quote_row["client_address"]:
        recipient_lines.append(quote_row["client_address"])
    if quote_row["client_contact_person"]:
        recipient_lines.append(quote_row["client_contact_person"])
    if quote_row["recipient_attention"]:
        recipient_lines.append(f"C/A {quote_row['recipient_attention']}")
    if quote_row["work_site"]:
        recipient_lines.append(quote_row["work_site"])

    left_content = "<br/>".join(_normalize_paragraph(line) for line in recipient_lines if line)
    right_lines = ["Data offerta", quote_row["offer_date"] or _fallback_offer_date(quote_row)]
    right_content = "<br/>".join(f"<b>{_normalize_paragraph(line)}</b>" for line in right_lines if line)

    table = Table(
        [[Paragraph(left_content, styles["body"]), Paragraph(right_content, styles["right"])]],
        colWidths=[105 * mm, 60 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#b9c7d8")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [table]


def _build_reference_panel(quote_row, styles):
    rows = [
        [Paragraph("Committente", styles["label"]), Paragraph(_normalize_paragraph(quote_row["client_name"]), styles["meta"])],
        [Paragraph("Oggetto", styles["label"]), Paragraph(_normalize_paragraph(quote_row["title"]), styles["meta"])],
    ]

    if quote_row["recipient_attention"]:
        rows.append(
            [
                Paragraph("C.A.", styles["label"]),
                Paragraph(_normalize_paragraph(quote_row["recipient_attention"]), styles["meta"]),
            ]
        )

    if quote_row["work_site"]:
        rows.append(
            [
                Paragraph("Cantiere / sito", styles["label"]),
                Paragraph(_normalize_paragraph(quote_row["work_site"]), styles["meta"]),
            ]
        )

    if quote_row["client_address"]:
        rows.append(
            [
                Paragraph("Indirizzo", styles["label"]),
                Paragraph(_normalize_paragraph(quote_row["client_address"]), styles["meta"]),
            ]
        )

    if quote_row["client_contact_person"]:
        rows.append(
            [
                Paragraph("Referente", styles["label"]),
                Paragraph(_normalize_paragraph(quote_row["client_contact_person"]), styles["meta"]),
            ]
        )

    description_text = (quote_row["description"] or "").strip()
    if description_text:
        rows.append(
            [
                Paragraph("Descrizione sintetica", styles["label"]),
                Paragraph(_normalize_paragraph(description_text), styles["meta"]),
            ]
        )

    table = Table(rows, colWidths=[42 * mm, 123 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f8")),
                ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#b9c7d8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d3dde7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _build_bullet_list(lines, styles):
    items = [ListItem(Paragraph(_normalize_paragraph(line), styles["body"])) for line in lines]
    return ListFlowable(items, bulletType="bullet", leftIndent=12, bulletFontName="Helvetica")


def _build_items_table(item_rows):
    data = [["N.", "Descrizione lavorazioni e forniture", "Q.ta", "Prezzo unit.", "Importo"]]
    total_amount = 0.0
    for item_row in item_rows:
        row_total = float(item_row["total_amount"])
        total_amount += row_total
        data.append(
            [
                str(item_row["line_number"]),
                item_row["description"],
                f"{float(item_row['quantity']):.2f}",
                _format_eur(float(item_row["unit_price"])),
                _format_eur(row_total),
            ]
        )

    data.append(["", "Totale lavorazioni", "", "", _format_eur(total_amount)])

    table = Table(data, colWidths=[12 * mm, 84 * mm, 18 * mm, 31 * mm, 30 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.3),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c4d1dd")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f5f8fb")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e7edf4")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    table.repeatRows = 1
    return table


def _build_amount_table(quote_row, item_rows):
    quoted_amount_value = float(quote_row["amount"] or 0.0)
    metric_total = sum(float(item_row["total_amount"]) for item_row in item_rows)
    rows = []
    if item_rows:
        rows.append(["Totale computo", _format_eur(metric_total)])
    rows.append(["Per un costo totale di", f"{_format_eur(quoted_amount_value)} + IVA"])
    table = Table(rows, colWidths=[46 * mm, 55 * mm], hAlign="RIGHT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -2), colors.HexColor("#eef3f8")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#16324f")),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#16324f")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _build_signature_block():
    stamp_image = _build_stamp_signature_image()
    if stamp_image is None:
        fallback = Table([["", f"{COMPANY_NAME}\n{DEFAULT_SIGNATURE}"]], colWidths=[90 * mm, 75 * mm])
        fallback.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ]
            )
        )
        return fallback

    table = Table([["", stamp_image]], colWidths=[85 * mm, 80 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _build_logo_image():
    image_path = _find_asset("logo")
    if image_path is None:
        return None
    image = Image(str(image_path))
    image._restrictSize(36 * mm, 36 * mm)
    return image


def _build_stamp_signature_image():
    image_path = _find_asset("timbro_firma")
    if image_path is None:
        return None
    image = Image(str(image_path))
    image._restrictSize(72 * mm, 38 * mm)
    return image


def _find_asset(base_name: str):
    for extension in ("png", "jpg", "jpeg"):
        candidate = ASSETS_DIR / f"{base_name}.{extension}"
        if candidate.exists():
            return candidate
    return None


def _build_output_filename(quote_row) -> str:
    progressive_number = int(quote_row["progressive_number"])
    title = _sanitize_filename_part(quote_row["title"])
    return f"Offerta {progressive_number} San Vincenzo srl - {title}.pdf"


def _sanitize_filename_part(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', " ", str(value)).strip()
    cleaned = re.sub(r'\s+', " ", cleaned)
    return cleaned[:120] or "Offerta"


def _build_offer_number(quote_row) -> str:
    offer_year = _extract_year(quote_row["offer_date"] or _fallback_offer_date(quote_row))
    return f"Offerta N. {int(quote_row['progressive_number'])} /{offer_year}"


def _extract_year(date_text: str) -> str:
    if not date_text:
        return str(datetime.now().year)
    for separator in ("/", "-", "."):
        if separator in date_text:
            parts = [part.strip() for part in date_text.split(separator) if part.strip()]
            if parts:
                tail = parts[-1]
                if len(tail) == 4 and tail.isdigit():
                    return tail
    digits = "".join(character for character in date_text if character.isdigit())
    if len(digits) >= 4:
        return digits[-4:]
    return str(datetime.now().year)


def _fallback_offer_date(quote_row) -> str:
    created_at = quote_row["created_at"] or ""
    if not created_at:
        return datetime.now().strftime("%d/%m/%Y")
    date_part = str(created_at).split(" ")[0]
    if "-" in date_part:
        year, month, day = date_part.split("-")
        return f"{day}/{month}/{year}"
    return date_part


def _extract_bullet_lines(quote_row, item_rows):
    custom_lines = [line.strip() for line in str(quote_row["included_items_text"] or "").splitlines() if line.strip()]
    if custom_lines:
        return custom_lines
    return [item_row["description"] for item_row in item_rows if item_row["description"]]


def _format_eur(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"EUR {formatted}"


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str) and value.isdigit():
        return bool(int(value))
    return bool(value)


def _normalize_paragraph(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
