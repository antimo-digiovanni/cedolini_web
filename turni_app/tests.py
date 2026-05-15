from django.test import SimpleTestCase

from .pdf_export import _build_portineria_weekly_sheet_table, _styles
from .workbook import WeeklySectionData


class PortineriaWeeklyExportTests(SimpleTestCase):
    def test_first_assignment_row_keeps_shift_label(self):
        sections = [
            WeeklySectionData(
                label="1 turno",
                time_label="06:14",
                time_values=["06:14", "08:17", "06:14"],
                rows=[
                    ["MENNA", "PANTANO", "RICCARDI"],
                    ["RICCARDI MARTEDI", "", "LUNEDI, MARTEDI VARRIALE"],
                    ["", "", ""],
                ],
            ),
            WeeklySectionData(
                label="2 turno",
                time_label="14:22",
                time_values=["14:22", "", "14:22"],
                rows=[
                    ["MINICHINI", "", "DE PALMA"],
                    ["", "", ""],
                    ["", "", ""],
                ],
            ),
            WeeklySectionData(
                label="3 turno",
                time_label="22:06",
                time_values=["22:06", "", "22:06"],
                rows=[
                    ["CORBO", "", "OREFICE"],
                    ["", "", ""],
                    ["", "", ""],
                ],
            ),
        ]

        table = _build_portineria_weekly_sheet_table(
            headers=["PORTINERIA CENTRALE", "CENTRALINISTA", "PORTINERIA CELLA"],
            sections=sections,
            styles=_styles(),
            fill_width_mm=190,
            target_height_mm=240,
        )

        self.assertEqual(table._cellvalues[3][0].getPlainText(), "1°")
        self.assertEqual(table._cellvalues[7][0].getPlainText(), "2°")
        self.assertEqual(table._cellvalues[11][0].getPlainText(), "3°")