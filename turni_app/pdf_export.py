from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import tempfile
from typing import Iterable
from xml.sax.saxutils import escape

import pypdfium2 as pdfium
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .workbook import WEEKEND_COLUMN_LABELS, WeeklySectionData


BRAND_NAVY = colors.HexColor("#0F172A")
BRAND_BLUE = colors.HexColor("#1D4ED8")
BRAND_BLUE_SOFT = colors.HexColor("#DBEAFE")
BRAND_BLUE_LIGHT = colors.HexColor("#EFF6FF")
BRAND_BORDER = colors.HexColor("#BFDBFE")
BRAND_TEXT = colors.HexColor("#0B1220")
BRAND_MUTED = colors.HexColor("#334155")

WEEKLY_PDF_NAME = "Turno settimanale.pdf"
SATURDAY_PDF_NAME = "Comandata sabato.pdf"
SUNDAY_PDF_NAME = "Comandata domenica.pdf"
WEEKLY_IMAGE_NAME = "Turno settimanale.jpg"
SATURDAY_IMAGE_NAME = "Comandata sabato.jpg"
SUNDAY_IMAGE_NAME = "Comandata domenica.jpg"
WEEKEND_SIGNATURE_HEADERS = (
    "FIRMA COMMITTENTE",
    "FIRMA RESPONSABILE AREA",
    "FIRMA LEGGIBILE",
)
WEEKLY_PRIMARY_COLUMN_INDEXES = (0, 1, 2, 3, 4, 5, 7)
WEEKLY_SECONDARY_COLUMN_INDEXES = (6, 8, 9)
WEEKLY_DEPARTMENT_MARKERS = {
    "PALAZZINA",
    "LARA",
    "M.M.D. BUILER",
    "M.M.D BUILER",
}


@dataclass(frozen=True)
class WeekendExportData:
    title: str
    authorization_date: str
    rows: list[list[str]]


class WeekendPdfCanvas(pdf_canvas.Canvas):
    def __init__(
        self,
        *args,
        styles: dict[str, ParagraphStyle],
        logo_path: Path | None,
        cert_logo_path: Path | None,
        anid_logo_path: Path | None,
        left_margin: float,
        right_margin: float,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict] = []
        self._weekend_styles = styles
        self._weekend_logo_path = logo_path
        self._weekend_cert_logo_path = cert_logo_path
        self._weekend_anid_logo_path = anid_logo_path
        self._left_margin = left_margin
        self._right_margin = right_margin

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        for state in self._saved_page_states:
            self.__dict__.update(state)
            _draw_weekend_page_overlay(
                self,
                styles=self._weekend_styles,
                logo_path=self._weekend_logo_path,
                cert_logo_path=self._weekend_cert_logo_path,
                anid_logo_path=self._weekend_anid_logo_path,
                left_margin=self._left_margin,
                right_margin=self._right_margin,
            )
            super().showPage()
        super().save()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titleBanner": ParagraphStyle(
            "TurniTitleBanner",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=22,
            alignment=0,
            textColor=colors.white,
        ),
        "weekBanner": ParagraphStyle(
            "TurniWeekBanner",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=13,
            alignment=0,
            textColor=colors.white,
        ),
        "title": ParagraphStyle(
            "TurniTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=13,
            alignment=1,
            textColor=BRAND_BLUE,
            spaceAfter=1,
        ),
        "subtitle": ParagraphStyle(
            "TurniSubtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.1,
            leading=7.7,
            alignment=1,
            textColor=BRAND_MUTED,
        ),
        "meta": ParagraphStyle(
            "TurniMeta",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=8.1,
            alignment=1,
            textColor=BRAND_NAVY,
            spaceBefore=1,
        ),
        "footer": ParagraphStyle(
            "TurniFooter",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=8.1,
            alignment=0,
            textColor=BRAND_NAVY,
        ),
        "certTitle": ParagraphStyle(
            "TurniCertTitle",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.1,
            leading=6.4,
            alignment=1,
            textColor=BRAND_MUTED,
        ),
        "certBody": ParagraphStyle(
            "TurniCertBody",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=5.4,
            leading=5.7,
            alignment=1,
            textColor=BRAND_MUTED,
        ),
        "certMini": ParagraphStyle(
            "TurniCertMini",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=4.6,
            leading=4.9,
            alignment=1,
            textColor=BRAND_MUTED,
        ),
        "section": ParagraphStyle(
            "TurniSection",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=8.1,
            leading=8.8,
            alignment=0,
            textColor=BRAND_NAVY,
            spaceAfter=2,
            spaceBefore=1,
        ),
        "small": ParagraphStyle(
            "TurniSmall",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.3,
            leading=6.8,
            alignment=1,
            textColor=BRAND_TEXT,
        ),
        "smallBold": ParagraphStyle(
            "TurniSmallBold",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.45,
            leading=6.9,
            alignment=1,
            textColor=BRAND_TEXT,
        ),
        "tiny": ParagraphStyle(
            "TurniTiny",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=5.9,
            leading=6.3,
            alignment=1,
            textColor=BRAND_TEXT,
        ),
        "miniTag": ParagraphStyle(
            "TurniMiniTag",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=5.6,
            leading=6.1,
            alignment=1,
            textColor=BRAND_NAVY,
        ),
        "headerBig": ParagraphStyle(
            "TurniHeaderBig",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.8,
            leading=9.4,
            alignment=1,
            textColor=BRAND_NAVY,
        ),
        "turnoBand": ParagraphStyle(
            "TurniTurnoBand",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=7.3,
            alignment=1,
            textColor=BRAND_NAVY,
        ),
        "shiftBand": ParagraphStyle(
            "TurniShiftBand",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=10.4,
            alignment=1,
            textColor=BRAND_BLUE,
        ),
        "timeWhite": ParagraphStyle(
            "TurniTimeWhite",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.6,
            leading=9,
            alignment=1,
            textColor=colors.white,
        ),
        "bodyCell": ParagraphStyle(
            "TurniBodyCell",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=8.3,
            alignment=1,
            textColor=BRAND_TEXT,
        ),
    }


def _paragraph(text: str, style: ParagraphStyle, allow_markup: bool = False) -> Paragraph:
    if allow_markup:
        return Paragraph(text or "", style)
    safe = escape(text or "").replace("\n", "<br/>")
    return Paragraph(safe, style)


def _normalize_weekly_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _format_weekly_header(text: str) -> str:
    normalized = _normalize_weekly_text(text).upper()
    mapping = {
        "SVUOTAMENTO CESTE CARTA E PLASTICA E PULIZIA": "SVUOTAMENTO<br/>CESTE CARTA E<br/>PLASTICA E Pulizia",
        "NAVETTA IMPIANTO": "NAVETTA<br/>IMPIANTO",
        "IMPIANTO BANO": "IMPIANTO<br/>BANO",
        "STANZETTE": "STANZETTE",
        "LAVAGGIO CASSONI": "LAVAGGIO<br/>CASSONI",
        "PRODUZIONE DE NIGRIS": "PRODUZIONE<br/>DE NIGRIS",
        "LAVAGGIO FLAX TANGS E BIDONI": "LAVAGGIO FLAX<br/>TANGS E BIDONI",
        "CARRELLO MMD": "CARRELLO<br/>MMD",
        "SPACCIO": "SPACCIO",
        "SALA MIX": "SALA MIX",
    }
    return mapping.get(normalized, escape(_normalize_weekly_text(text)).replace(" ", "<br/>"))


def _header_block(title: str, lines: Iterable[str], logo_path: Path | None, styles: dict[str, ParagraphStyle]) -> Table:
    right = [_paragraph(title, styles["title"])]
    for line in lines:
        if line.strip():
            right.append(_paragraph(line, styles["subtitle"] if "SANVINCENZO" not in line else styles["meta"]))

    table = Table([[right]], colWidths=[265 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return table


def _build_weekly_table(
    headers: list[str],
    sections: list[WeeklySectionData],
    styles: dict[str, ParagraphStyle],
    column_indexes: tuple[int, ...],
    fill_width_mm: float,
) -> Table:
    selected_headers = [headers[index] for index in column_indexes]
    rows = [[_paragraph("TURNO", styles["smallBold"]), _paragraph("RIGA", styles["smallBold"])] + [_paragraph(_format_weekly_header(text), styles["tiny"], allow_markup=True) for text in selected_headers]]
    time_row_indexes: list[int] = []
    marker_cells: list[tuple[int, int]] = []
    short_labels = ("1°", "2°", "3°")
    for index, section in enumerate(sections):
        time_row_indexes.append(len(rows))
        rows.append([
            _paragraph(short_labels[index], styles["smallBold"]),
            _paragraph("ORARIO", styles["smallBold"]),
        ] + [_paragraph(section.time_values[column_index], styles["smallBold"]) for column_index in column_indexes])
        for row_number, assignment_row in enumerate(section.rows, start=1):
            current_row_index = len(rows)
            row_cells = [
                _paragraph(short_labels[index], styles["smallBold"]),
                _paragraph(str(row_number), styles["smallBold"]),
            ]
            for local_column_index, column_index in enumerate(column_indexes, start=2):
                normalized = _normalize_weekly_text(assignment_row[column_index])
                row_cells.append(_paragraph(normalized, styles["small"]))
                if normalized.upper() in WEEKLY_DEPARTMENT_MARKERS:
                    marker_cells.append((local_column_index, current_row_index))
            rows.append(row_cells)

    label_widths = [11 * mm, 10 * mm]
    remaining_width = max(fill_width_mm - sum(label_widths), 40)
    dynamic_width = remaining_width / max(len(column_indexes), 1)
    col_widths = label_widths + [dynamic_width] * len(column_indexes)
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF59D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_NAVY),
        ("GRID", (0, 0), (-1, -1), 0.45, BRAND_BORDER),
        ("BOX", (0, 0), (-1, -1), 0.8, BRAND_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("BACKGROUND", (0, 1), (1, -1), BRAND_BLUE_LIGHT),
    ]
    for row_index in time_row_indexes:
        style_commands.extend(
            [
                ("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#92D050")),
                ("TEXTCOLOR", (0, row_index), (-1, row_index), BRAND_NAVY),
                ("TOPPADDING", (0, row_index), (-1, row_index), 2.1),
                ("BOTTOMPADDING", (0, row_index), (-1, row_index), 2.1),
            ]
        )
    for column_index, row_index in marker_cells:
        style_commands.extend(
            [
                ("BACKGROUND", (column_index, row_index), (column_index, row_index), BRAND_BLUE_SOFT),
                ("TEXTCOLOR", (column_index, row_index), (column_index, row_index), BRAND_NAVY),
            ]
        )
    table.setStyle(TableStyle(style_commands))
    return table


def _join_secondary_row(values: list[str]) -> str:
    return " | ".join(_normalize_weekly_text(value) for value in values if _normalize_weekly_text(value))


def _build_weekly_secondary_table(
    headers: list[str],
    sections: list[WeeklySectionData],
    styles: dict[str, ParagraphStyle],
    fill_width_mm: float,
) -> Table:
    section_headers = [headers[index] for index in WEEKLY_SECONDARY_COLUMN_INDEXES]
    rows = [
        [_paragraph("TURNO", styles["smallBold"]), _paragraph("RIGA", styles["smallBold"])]
        + [_paragraph(_format_weekly_header(text), styles["tiny"], allow_markup=True) for text in section_headers]
    ]
    time_row_indexes: list[int] = []
    short_labels = ("1°", "2°", "3°")
    for index, section in enumerate(sections):
        time_row_indexes.append(len(rows))
        rows.append(
            [_paragraph(short_labels[index], styles["smallBold"]), _paragraph("ORARIO", styles["smallBold"])]
            + [_paragraph(section.time_values[column_index], styles["smallBold"]) for column_index in WEEKLY_SECONDARY_COLUMN_INDEXES]
        )
        rows.append(
            [_paragraph(short_labels[index], styles["smallBold"]), _paragraph("CENTRALE", styles["smallBold"])]
            + [
                _paragraph(_join_secondary_row([row[column_index] for row in section.rows]), styles["small"])
                for column_index in WEEKLY_SECONDARY_COLUMN_INDEXES
            ]
        )

    label_widths = [11 * mm, 16 * mm]
    remaining_width = max(fill_width_mm - sum(label_widths), 40)
    dynamic_width = remaining_width / max(len(WEEKLY_SECONDARY_COLUMN_INDEXES), 1)
    table = Table(rows, colWidths=label_widths + [dynamic_width] * len(WEEKLY_SECONDARY_COLUMN_INDEXES), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF9C4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_NAVY),
                ("GRID", (0, 0), (-1, -1), 0.45, BRAND_BORDER),
                ("BOX", (0, 0), (-1, -1), 0.8, BRAND_BLUE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 1.6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1.6),
                ("TOPPADDING", (0, 0), (-1, -1), 2.1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.1),
                ("BACKGROUND", (0, 1), (1, -1), BRAND_BLUE_LIGHT),
                ("ROWBACKGROUNDS", (2, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]
        )
    )
    extra_styles: list[tuple] = []
    for row_index in time_row_indexes:
        extra_styles.extend(
            [
                ("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#92D050")),
                ("TEXTCOLOR", (0, row_index), (-1, row_index), BRAND_NAVY),
            ]
        )
    table.setStyle(TableStyle(extra_styles))
    return table


def _build_weekly_title_table(
    title_text: str,
    week_label: str,
    styles: dict[str, ParagraphStyle],
    fill_width_mm: float,
) -> Table:
    table = Table(
        [
            [_paragraph(title_text, styles["titleBanner"])],
            [_paragraph(week_label, styles["weekBanner"])],
        ],
        colWidths=[fill_width_mm * mm],
        rowHeights=[10 * mm, 8 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), BRAND_NAVY),
                ("BACKGROUND", (0, 1), (0, 1), BRAND_BLUE),
                ("TEXTCOLOR", (0, 0), (0, 1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.8, BRAND_NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _draw_weekly_watermark(canvas, doc, logo_path: Path | None) -> None:
    if not logo_path or not logo_path.exists():
        return
    page_width, page_height = doc.pagesize
    watermark_size = 115 * mm
    x = (page_width - watermark_size) / 2
    y = (page_height - watermark_size) / 2 - (10 * mm)
    canvas.saveState()
    if hasattr(canvas, "setFillAlpha"):
        canvas.setFillAlpha(0.08)
    canvas.drawImage(str(logo_path), x, y, width=watermark_size, height=watermark_size, mask="auto", preserveAspectRatio=True)
    canvas.restoreState()


def _draw_weekend_footer(canvas, doc, styles: dict[str, ParagraphStyle]) -> None:
    footer_lines = [
        "Firma per Autorizzazione servizi generali  MAGNUM ICE CREAM",
        "________________________________________________________________",
        "TELEFONO URGENZE CELLULARE 3355984445",
    ]
    page_width, _ = doc.pagesize
    left_x = doc.leftMargin
    bottom_y = 3.8 * mm
    available_width = page_width - doc.leftMargin - doc.rightMargin

    canvas.saveState()
    current_y = bottom_y + (6.4 * mm)
    for text in footer_lines:
        paragraph = _paragraph(text, styles["footer"])
        width, height = paragraph.wrap(available_width, 20 * mm)
        paragraph.drawOn(canvas, left_x, current_y)
        current_y -= height + (0.4 * mm)
    canvas.restoreState()


def _draw_weekend_page(canvas, doc, styles: dict[str, ParagraphStyle], logo_path: Path | None) -> None:
    _draw_weekend_footer(canvas, doc, styles)


def _draw_weekend_page_overlay(
    canvas,
    *,
    styles: dict[str, ParagraphStyle],
    logo_path: Path | None,
    cert_logo_path: Path | None,
    anid_logo_path: Path | None,
    left_margin: float,
    right_margin: float,
) -> None:
    page_width, page_height = canvas._pagesize

    if logo_path and logo_path.exists():
        watermark_size = 118 * mm
        x = (page_width - watermark_size) / 2
        y = (page_height - watermark_size) / 2 - (8 * mm)
        canvas.saveState()
        if hasattr(canvas, "setFillAlpha"):
            canvas.setFillAlpha(0.06)
        canvas.drawImage(str(logo_path), x, y, width=watermark_size, height=watermark_size, mask="auto", preserveAspectRatio=True)
        canvas.restoreState()

    cert_panel_width = 86 * mm
    cert_panel_height = 27 * mm
    cert_panel_x = page_width - right_margin - cert_panel_width
    cert_panel_y = 3.8 * mm

    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#DCE8F8"))
    canvas.roundRect(cert_panel_x + 0.8 * mm, cert_panel_y - 0.8 * mm, cert_panel_width, cert_panel_height, 3 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.roundRect(cert_panel_x, cert_panel_y, cert_panel_width, cert_panel_height, 3 * mm, fill=1, stroke=0)
    canvas.restoreState()

    logo_box_width = 21 * mm
    logo_box_height = 10.5 * mm
    logo_top_y = cert_panel_y + cert_panel_height - logo_box_height - (2.3 * mm)
    gap = 5 * mm
    first_logo_x = cert_panel_x + ((cert_panel_width - ((logo_box_width * 3) + (gap * 2))) / 2)
    logo_slots = [
        (logo_path, first_logo_x),
        (cert_logo_path, first_logo_x + logo_box_width + gap),
        (anid_logo_path, first_logo_x + ((logo_box_width + gap) * 2)),
    ]
    for image_path, slot_x in logo_slots:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D7E4F7"))
        canvas.setLineWidth(0.35)
        canvas.roundRect(slot_x, logo_top_y, logo_box_width, logo_box_height, 1.8 * mm, fill=0, stroke=1)
        if image_path and image_path.exists():
            canvas.drawImage(
                str(image_path),
                slot_x + (0.7 * mm),
                logo_top_y + (0.7 * mm),
                width=logo_box_width - (1.4 * mm),
                height=logo_box_height - (1.4 * mm),
                mask="auto",
                preserveAspectRatio=True,
                anchor="c",
            )
        canvas.restoreState()

    separator_y = cert_panel_y + (11.6 * mm)
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E4F7"))
    canvas.setLineWidth(0.4)
    canvas.line(cert_panel_x + (4 * mm), separator_y, cert_panel_x + cert_panel_width - (4 * mm), separator_y)
    canvas.restoreState()

    text_width = cert_panel_width - (8 * mm)
    text_x = cert_panel_x + (4 * mm)
    text_story = [
        _paragraph("Organismo accreditato da ACCREDIA", styles["certMini"]),
        _paragraph("Certificazione SGQ / SGA  |  UNI EN 16636 N.102PSE", styles["certBody"]),
        _paragraph("Associata ANID", styles["certMini"]),
    ]
    current_y = separator_y - (1.1 * mm)
    for paragraph in text_story:
        _, paragraph_height = paragraph.wrap(text_width, 8 * mm)
        paragraph.drawOn(canvas, text_x, current_y - paragraph_height)
        current_y -= paragraph_height + (0.35 * mm)

    canvas.saveState()
    canvas.setStrokeColor(BRAND_BLUE)
    canvas.setLineWidth(0.7)
    canvas.roundRect(cert_panel_x, cert_panel_y, cert_panel_width, cert_panel_height, 3 * mm, fill=0, stroke=1)
    canvas.restoreState()

    footer_lines = [
        "Firma per Autorizzazione servizi generali  MAGNUM ICE CREAM",
        "________________________________________________________________",
        "TELEFONO URGENZE CELLULARE 3355984445",
    ]
    available_width = page_width - left_margin - right_margin - cert_panel_width - (5 * mm)
    bottom_y = 3.8 * mm

    canvas.saveState()
    current_y = bottom_y + (6.4 * mm)
    for text in footer_lines:
        paragraph = _paragraph(text, styles["footer"])
        _, height = paragraph.wrap(available_width, 20 * mm)
        paragraph.drawOn(canvas, left_margin, current_y)
        current_y -= height + (0.4 * mm)
    canvas.restoreState()


def _build_weekly_sheet_table(
    headers: list[str],
    sections: list[WeeklySectionData],
    styles: dict[str, ParagraphStyle],
    fill_width_mm: float,
) -> Table:
    rows: list[list[Paragraph]] = []
    rows.append([_paragraph("", styles["smallBold"])] + [_paragraph("REPARTO", styles["miniTag"]) for _ in headers])
    rows.append([_paragraph("T<br/>U<br/>R<br/>N<br/>O", styles["turnoBand"], allow_markup=True)] + [_paragraph(_format_weekly_header(text), styles["headerBig"], allow_markup=True) for text in headers])

    marker_cells: list[tuple[int, int]] = []
    accent_rows: list[int] = []
    time_row_indexes: list[int] = []
    row_heights = [5 * mm, 14 * mm]
    for index, section in enumerate(sections):
        time_row_indexes.append(len(rows))
        time_label_cell = Spacer(1, 1) if index == 3 else _paragraph("", styles["smallBold"])
        rows.append([time_label_cell] + [_paragraph(value, styles["timeWhite"]) for value in section.time_values])
        row_heights.append(7 * mm)
        for row_number, assignment_row in enumerate(section.rows):
            current_row_index = len(rows)
            is_accent_row = index == 2 and row_number == 2
            if is_accent_row:
                blank_turn_row = [_paragraph("3°", styles["shiftBand"])] + [_paragraph("", styles["bodyCell"]) for _ in headers]
                rows.append(blank_turn_row)
                row_heights.append(9.5 * mm)
                current_row_index = len(rows)

            shift_label = "" if index == 3 or is_accent_row else f"{index + 1}°"
            label = Spacer(1, 1) if shift_label == "" else _paragraph(shift_label, styles["shiftBand"])
            row_cells = [label]
            for column_index, value in enumerate(assignment_row):
                normalized = _normalize_weekly_text(value)
                row_cells.append(_paragraph(normalized, styles["headerBig"] if is_accent_row else styles["bodyCell"]))
                if normalized.upper() in WEEKLY_DEPARTMENT_MARKERS:
                    marker_cells.append((column_index + 1, current_row_index))
            if is_accent_row:
                accent_rows.append(current_row_index)
            rows.append(row_cells)
            row_heights.append(9.5 * mm)

    first_col_width = 8 * mm
    remaining_width = max(fill_width_mm - first_col_width, 60)
    column_widths = [first_col_width]
    weights = [1.05, 0.95, 0.95, 0.85, 1.0, 1.1, 1.05, 1.1, 0.9, 0.9]
    total_weight = sum(weights)
    for weight in weights:
        column_widths.append((remaining_width * (weight / total_weight)) * mm)

    table = Table(rows, colWidths=column_widths, rowHeights=row_heights)
    style_commands: list[tuple] = [
        ("GRID", (0, 0), (-1, -1), 0.45, BRAND_NAVY),
        ("BOX", (0, 0), (-1, -1), 0.8, BRAND_NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.6),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE_LIGHT),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#EAF2FF")),
        ("BACKGROUND", (0, 1), (0, len(rows) - 1), BRAND_BLUE_LIGHT),
    ]
    for time_row in time_row_indexes:
        style_commands.extend(
            [
                ("BACKGROUND", (0, time_row), (-1, time_row), BRAND_BLUE),
                ("TEXTCOLOR", (0, time_row), (-1, time_row), colors.white),
            ]
        )
    for accent_row in accent_rows:
        style_commands.extend(
            [
                ("BACKGROUND", (0, accent_row), (-1, accent_row), BRAND_BLUE_LIGHT),
                ("TEXTCOLOR", (0, accent_row), (-1, accent_row), BRAND_NAVY),
            ]
        )
    for marker_column, marker_row in marker_cells:
        style_commands.extend(
            [
                ("BACKGROUND", (marker_column, marker_row), (marker_column, marker_row), BRAND_BLUE_SOFT),
                ("TEXTCOLOR", (marker_column, marker_row), (marker_column, marker_row), BRAND_NAVY),
            ]
        )
    table.setStyle(TableStyle(style_commands))
    return table


def _build_weekend_table(
    rows: list[list[str]],
    styles: dict[str, ParagraphStyle],
    fill_width_mm: float,
    target_height_mm: float,
) -> Table:
    header = list(WEEKEND_COLUMN_LABELS) + list(WEEKEND_SIGNATURE_HEADERS)
    body = [row + ["", "", ""] for row in rows]
    body_row_count = max(len(body), 1)

    if body_row_count >= 38:
        header_style = ParagraphStyle("WeekendHeaderCompact", parent=styles["smallBold"], fontSize=5.45, leading=5.6)
        body_style = ParagraphStyle("WeekendBodyCompact", parent=styles["small"], fontSize=5.15, leading=5.35)
    elif body_row_count >= 32:
        header_style = ParagraphStyle("WeekendHeaderMedium", parent=styles["smallBold"], fontSize=5.95, leading=6.2)
        body_style = ParagraphStyle("WeekendBodyMedium", parent=styles["small"], fontSize=5.55, leading=5.8)
    else:
        header_style = styles["smallBold"]
        body_style = styles["small"]

    data = [[_paragraph(text, header_style) for text in header]]
    data.extend([[_paragraph(text, body_style) for text in row] for row in body])

    base_widths_mm = [21, 17, 31, 24, 32, 26, 34, 36, 29]
    width_scale = fill_width_mm / sum(base_widths_mm)
    col_widths = [width * width_scale * mm for width in base_widths_mm]

    header_height_mm = 8.8
    available_body_height_mm = max(0.0, target_height_mm - header_height_mm)
    body_height_mm = min(4.0, max(2.2, available_body_height_mm / body_row_count))
    row_heights = [header_height_mm * mm] + [body_height_mm * mm for _ in body]

    table = Table(data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCEBFF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_NAVY),
                ("GRID", (0, 0), (-1, -1), 0.45, BRAND_BORDER),
                ("BOX", (0, 0), (-1, -1), 0.8, BRAND_BLUE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.8),
                ("TOPPADDING", (0, 0), (-1, -1), 1.1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.1),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_BLUE_LIGHT]),
            ]
        )
    )
    return table


def _cleanup_existing_image_outputs(output_path: Path) -> None:
    if output_path.exists():
        output_path.unlink()
    for existing_file in output_path.parent.glob(f"{output_path.stem}_*.jpg"):
        existing_file.unlink()


def _render_pdf_to_jpg_files(pdf_path: Path, output_path: Path, dpi: int = 200) -> list[Path]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _cleanup_existing_image_outputs(output_path)

    pdf_document = pdfium.PdfDocument(str(pdf_path))
    try:
        exported_paths: list[Path] = []
        page_count = len(pdf_document)
        scale = dpi / 72
        for page_index in range(page_count):
            page = pdf_document[page_index]
            try:
                rendered_page = page.render(scale=scale)
                pil_image = rendered_page.to_pil()
                if pil_image.mode != "RGB":
                    pil_image = pil_image.convert("RGB")
                if page_count == 1:
                    current_output_path = output_path
                else:
                    current_output_path = output_path.with_name(f"{output_path.stem}_{page_index + 1:02d}.jpg")
                pil_image.save(current_output_path, format="JPEG", quality=95)
                exported_paths.append(current_output_path)
            finally:
                page.close()
        return exported_paths
    finally:
        pdf_document.close()


def export_weekly_pdf(
    output_path: Path,
    *,
    title_text: str,
    week_label: str,
    signature: str,
    headers: list[str],
    sections: list[WeeklySectionData],
    logo_path: Path | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=4 * mm,
        rightMargin=4 * mm,
        topMargin=4 * mm,
        bottomMargin=4 * mm,
    )
    total_width_mm = (landscape(A4)[0] / mm) - 8
    story = [
        _build_weekly_title_table(title_text, week_label, styles, total_width_mm),
        Spacer(1, 0.7 * mm),
        _build_weekly_sheet_table(headers, sections, styles, total_width_mm),
        Spacer(1, 0.8 * mm),
        _paragraph(signature, styles["footer"]),
    ]
    document.build(story, onFirstPage=lambda canvas, doc: _draw_weekly_watermark(canvas, doc, logo_path))
    return output_path


def export_weekly_images(
    output_path: Path,
    *,
    title_text: str,
    week_label: str,
    signature: str,
    headers: list[str],
    sections: list[WeeklySectionData],
    logo_path: Path | None = None,
) -> list[Path]:
    with tempfile.TemporaryDirectory(prefix="turni_planner_weekly_") as temp_dir:
        temp_pdf_path = Path(temp_dir) / WEEKLY_PDF_NAME
        export_weekly_pdf(
            temp_pdf_path,
            title_text=title_text,
            week_label=week_label,
            signature=signature,
            headers=headers,
            sections=sections,
            logo_path=logo_path,
        )
        return _render_pdf_to_jpg_files(temp_pdf_path, output_path)


def export_weekly_outputs(
    output_dir: Path,
    *,
    title_text: str,
    week_label: str,
    signature: str,
    headers: list[str],
    sections: list[WeeklySectionData],
    logo_path: Path | None = None,
) -> tuple[Path, list[Path]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / WEEKLY_PDF_NAME
    image_path = output_dir / WEEKLY_IMAGE_NAME
    export_weekly_pdf(
        pdf_path,
        title_text=title_text,
        week_label=week_label,
        signature=signature,
        headers=headers,
        sections=sections,
        logo_path=logo_path,
    )
    return pdf_path, _render_pdf_to_jpg_files(pdf_path, image_path)


def export_weekend_pdf(
    output_path: Path,
    *,
    data: WeekendExportData,
    logo_path: Path | None = None,
    cert_logo_path: Path | None = None,
    anid_logo_path: Path | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    page_width_mm = landscape(A4)[0] / mm
    page_height_mm = landscape(A4)[1] / mm
    horizontal_margin_mm = 4
    vertical_margin_mm = 3.5
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        leftMargin=horizontal_margin_mm * mm,
        rightMargin=horizontal_margin_mm * mm,
        topMargin=vertical_margin_mm * mm,
        bottomMargin=vertical_margin_mm * mm,
    )
    table_width_mm = page_width_mm - (horizontal_margin_mm * 2)
    table_height_mm = page_height_mm - (vertical_margin_mm * 2) - 23
    story = [
        _header_block(
            data.title,
            [
                "SANVINCENZO S.R.L - ORGANIZZAZIONE TURNI COMANDATE",
                f"{data.authorization_date}  Autorizzazione ingresso del personale sottoelencato da Voi richiestoci.",
            ],
            logo_path,
            styles,
        ),
        Spacer(1, 1 * mm),
        _build_weekend_table(data.rows, styles, table_width_mm, table_height_mm),
    ]
    document.build(
        story,
        canvasmaker=lambda *args, **kwargs: WeekendPdfCanvas(
            *args,
            styles=styles,
            logo_path=logo_path,
            cert_logo_path=cert_logo_path,
            anid_logo_path=anid_logo_path,
            left_margin=document.leftMargin,
            right_margin=document.rightMargin,
            **kwargs,
        ),
    )
    return output_path


def export_weekend_images(
    output_path: Path,
    *,
    data: WeekendExportData,
    logo_path: Path | None = None,
    cert_logo_path: Path | None = None,
    anid_logo_path: Path | None = None,
) -> list[Path]:
    with tempfile.TemporaryDirectory(prefix="turni_planner_weekend_") as temp_dir:
        temp_pdf_path = Path(temp_dir) / SATURDAY_PDF_NAME
        export_weekend_pdf(
            temp_pdf_path,
            data=data,
            logo_path=logo_path,
            cert_logo_path=cert_logo_path,
            anid_logo_path=anid_logo_path,
        )
        return _render_pdf_to_jpg_files(temp_pdf_path, output_path)


def export_weekend_outputs(
    output_dir: Path,
    *,
    pdf_name: str,
    image_name: str,
    data: WeekendExportData,
    logo_path: Path | None = None,
    cert_logo_path: Path | None = None,
    anid_logo_path: Path | None = None,
) -> tuple[Path, list[Path]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / pdf_name
    image_path = output_dir / image_name
    export_weekend_pdf(
        pdf_path,
        data=data,
        logo_path=logo_path,
        cert_logo_path=cert_logo_path,
        anid_logo_path=anid_logo_path,
    )
    return pdf_path, _render_pdf_to_jpg_files(pdf_path, image_path)