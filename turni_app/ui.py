from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Iterable

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt, QSettings, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QKeySequence, QPalette, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCompleter,
    QDockWidget,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetSelectionRange,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .pdf_export import (
    PORTINERIA_WEEKEND_IMAGE_NAME,
    PORTINERIA_WEEKEND_PDF_NAME,
    PORTINERIA_WEEKLY_IMAGE_NAME,
    PORTINERIA_WEEKLY_PDF_NAME,
    SATURDAY_PDF_NAME,
    SATURDAY_IMAGE_NAME,
    SUNDAY_PDF_NAME,
    SUNDAY_IMAGE_NAME,
    WEEKLY_PDF_NAME,
    WEEKLY_IMAGE_NAME,
    WeekendExportData,
    export_weekend_outputs,
    export_weekly_outputs,
)
from .workbook import WEEKEND_COLUMN_LABELS, TurniWorkbook, WeeklySectionData, WeekendSheetData


APP_NAME = "Turni Planner San Vincenzo"
ORG_NAME = "AntimoTools"
def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


BASE_DIR = _runtime_base_dir()
APP_LOGO_PATH = BASE_DIR / "portal" / "static" / "portal" / "logo.png"
APP_ICON_PATH = BASE_DIR / "portal" / "static" / "portal" / "icons" / "icon-512.png"
WEEKEND_ANCIS_LOGO_PATH = BASE_DIR / "portal" / "static" / "portal" / "ancis-sgq-sga-2026.png"
WEEKEND_ANID_LOGO_PATH = BASE_DIR / "portal" / "static" / "portal" / "logo-anid.jpg"
DEFAULT_WEEKLY_PDF_TITLE = "SANVINCENZO S.R.L.:ORGANIZZAZIONE TURNI"
PDF_OUTPUT_DIR_SETTING = "pdfOutputDirectory"
WEEKLY_PRIMARY_COLUMN_INDEXES = (0, 1, 2, 3, 4, 5, 7)
WEEKLY_SECONDARY_COLUMN_INDEXES = (6, 8, 9)
WEEKLY_ALL_COLUMN_INDEXES = tuple(range(10))
WEEK_SELECTOR_YEAR = 2026
WEEK_SELECTOR_COUNT = 52
WINDOW_LAYOUT_VERSION = 4
PORTINERIA_WEEKEND_ROW_COUNT = 34
PORTINERIA_DATA_COLUMNS = (1, 3, 4)
PORTINERIA_HEADERS = ("PORTINERIA CENTRALE", "CENTRALINISTA", "PORTINERIA CELLA")
PORTINERIA_DEFAULT_TIMES = (
    ("06:14", "08:17", "06:14"),
    ("14:22", "", "14:22"),
    ("22:06", "", "22:06"),
)


def _week_start_for_number(week_number: int) -> datetime:
    return datetime.fromisocalendar(WEEK_SELECTOR_YEAR, week_number, 1)


def _format_week_label_from_number(week_number: int) -> str:
    start_date = _week_start_for_number(week_number)
    end_date = start_date + timedelta(days=5)
    return f"Week: {week_number:02d} da Lunedi {start_date:%d/%m/%Y} a Sabato {end_date:%d/%m/%Y}"


def _infer_week_number_from_text(text: str) -> int | None:
    clean = text.strip()
    if not clean:
        return None

    week_match = re.search(r"\bweek\s*[:\-]?\s*(\d{1,2})\b", clean, re.IGNORECASE)
    if week_match:
        week_number = int(week_match.group(1))
        if 1 <= week_number <= WEEK_SELECTOR_COUNT:
            return week_number

    date_matches = re.findall(r"\b(\d{2}/\d{2}/\d{4})\b", clean)
    for date_text in date_matches:
        try:
            parsed_date = datetime.strptime(date_text, "%d/%m/%Y")
        except ValueError:
            continue
        iso_year, iso_week, _ = parsed_date.isocalendar()
        if iso_year == WEEK_SELECTOR_YEAR and 1 <= iso_week <= WEEK_SELECTOR_COUNT:
            return iso_week
    return None


def make_table_item(value: str) -> QTableWidgetItem:
    item = QTableWidgetItem(value)
    item.setTextAlignment(Qt.AlignCenter)
    return item


def _default_portineria_sections() -> list[WeeklySectionData]:
    sections: list[WeeklySectionData] = []
    for index, time_values in enumerate(PORTINERIA_DEFAULT_TIMES, start=1):
        sections.append(
            WeeklySectionData(
                label=f"{index} turno",
                time_label=time_values[0],
                time_values=list(time_values),
                rows=[["", "", ""] for _ in range(3)],
            )
        )
    return sections


class NameCompleterDelegate(QStyledItemDelegate):
    def __init__(self, names: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._names = names or []

    def set_names(self, names: list[str]) -> None:
        self._names = names

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            completer = QCompleter(self._names, editor)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            completer.setCompletionMode(QCompleter.PopupCompletion)
            editor.setCompleter(completer)
            editor.textEdited.connect(lambda _: completer.complete())
            editor.editingFinished.connect(lambda e=editor: self._apply_best_match(e))
        return editor

    def _apply_best_match(self, editor: QLineEdit) -> None:
        text = editor.text().strip()
        if not text:
            return
        lower_text = text.lower()
        matches = [name for name in self._names if lower_text in name.lower()]
        if len(matches) == 1:
            editor.setText(matches[0])


class SpreadsheetTableWidget(QTableWidget):
    operationCommitted = Signal(object, object, str)

    def __init__(self):
        super().__init__()
        self._name_delegate = NameCompleterDelegate(parent=self)
        self.setItemDelegate(self._name_delegate)
        self._fill_handle = QFrame(self.viewport())
        self._fill_handle.setFixedSize(8, 8)
        self._fill_handle.setStyleSheet("background:#2F61C8; border:1px solid white; border-radius:1px;")
        self._fill_handle.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._fill_handle.hide()
        self._fill_source_range: QTableWidgetSelectionRange | None = None
        self._fill_target_row: int | None = None
        self._fill_dragging = False
        self._move_drag_source: tuple[int, int] | None = None
        self._move_dragging = False
        self._press_pos: QPoint | None = None
        self._tracking_operation = False
        self._restoring_snapshot = False
        self._pending_edit_snapshot: list[list[str]] | None = None

        self.itemSelectionChanged.connect(self._update_fill_handle)
        self.currentCellChanged.connect(lambda *_: self._update_fill_handle())
        self.itemChanged.connect(self._handle_item_changed)

    def set_completion_names(self, names: list[str]) -> None:
        self._name_delegate.set_names(names)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copy_selection()
            event.accept()
            return
        if event.matches(QKeySequence.Paste):
            self.paste_selection()
            event.accept()
            return
        if event.key() == Qt.Key_Delete:
            selection_range = self._selection_range()
            if selection_range is not None:
                self._run_tracked_operation("Cancella celle", lambda: self._set_text_in_range(selection_range, ""))
                event.accept()
                return
        super().keyPressEvent(event)

    def edit(self, index, trigger, event):
        if index.isValid() and not self._tracking_operation and not self._restoring_snapshot and self._pending_edit_snapshot is None:
            item = self.item(index.row(), index.column())
            if item is not None and (item.flags() & Qt.ItemIsEditable):
                self._pending_edit_snapshot = self.snapshot_state()
        return super().edit(index, trigger, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._fill_handle.isVisible() and self._fill_handle.geometry().contains(event.position().toPoint()):
            selection_range = self._editable_selection_range()
            if selection_range is not None:
                self._fill_dragging = True
                self._fill_source_range = selection_range
                self._fill_target_row = selection_range.bottomRow()
                self.viewport().grabMouse()
                event.accept()
                return
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.position().toPoint())
            if index.isValid():
                item = self.item(index.row(), index.column())
                if item is not None and (item.flags() & Qt.ItemIsEditable):
                    self._move_drag_source = (index.row(), index.column())
                    self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._fill_dragging and self._fill_source_range is not None:
            target = self.indexAt(event.position().toPoint())
            if target.isValid():
                self._fill_target_row = max(target.row(), self._fill_source_range.bottomRow())
            event.accept()
            return
        if self._move_drag_source is not None and self._press_pos is not None:
            if (event.position().toPoint() - self._press_pos).manhattanLength() >= QApplication.startDragDistance():
                self._move_dragging = True
                self.viewport().setCursor(QCursor(Qt.ClosedHandCursor))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._fill_dragging:
            if self.viewport().mouseGrabber() is self.viewport():
                self.viewport().releaseMouse()
            self._apply_drag_fill()
            self._fill_dragging = False
            self._fill_source_range = None
            self._fill_target_row = None
            event.accept()
            return
        if self._move_dragging and self._move_drag_source is not None:
            target = self.indexAt(event.position().toPoint())
            self.viewport().unsetCursor()
            if target.isValid():
                self._move_cell_value(self._move_drag_source, (target.row(), target.column()))
            self._move_drag_source = None
            self._move_dragging = False
            self._press_pos = None
            event.accept()
            return
        self._move_drag_source = None
        self._move_dragging = False
        self._press_pos = None
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_fill_handle()

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        self._update_fill_handle()

    def copy_selection(self) -> None:
        selection_range = self._selection_range()
        if selection_range is None:
            return
        lines: list[str] = []
        for row in range(selection_range.topRow(), selection_range.bottomRow() + 1):
            cells: list[str] = []
            for column in range(selection_range.leftColumn(), selection_range.rightColumn() + 1):
                item = self.item(row, column)
                cells.append(item.text() if item else "")
            lines.append("\t".join(cells))
        QApplication.clipboard().setText("\n".join(lines))

    def paste_selection(self) -> None:
        raw_text = QApplication.clipboard().text()
        if not raw_text:
            return
        rows = [line.split("\t") for line in raw_text.replace("\r\n", "\n").split("\n")]
        if rows and rows[-1] == [""]:
            rows.pop()
        if not rows:
            return

        selection_range = self._selection_range()
        if selection_range is not None:
            start_row = selection_range.topRow()
            start_column = selection_range.leftColumn()
        else:
            start_row = max(self.currentRow(), 0)
            start_column = max(self.currentColumn(), 0)

        if len(rows) == 1 and len(rows[0]) == 1 and selection_range is not None:
            self._run_tracked_operation("Incolla celle", lambda: self._set_text_in_range(selection_range, rows[0][0]))
            return

        def paste_action() -> None:
            for row_offset, row_values in enumerate(rows):
                for column_offset, value in enumerate(row_values):
                    row_index = start_row + row_offset
                    column_index = start_column + column_offset
                    if row_index >= self.rowCount() or column_index >= self.columnCount():
                        continue
                    self._set_cell_text(row_index, column_index, value)

        self._run_tracked_operation("Incolla celle", paste_action)

    def _apply_drag_fill(self) -> None:
        if self._fill_source_range is None or self._fill_target_row is None:
            return
        source = self._fill_source_range
        if self._fill_target_row <= source.bottomRow():
            return

        def fill_action() -> None:
            pattern_height = source.rowCount()
            pattern_width = source.columnCount()
            for row in range(source.bottomRow() + 1, self._fill_target_row + 1):
                source_row = source.topRow() + ((row - source.topRow()) % pattern_height)
                for column in range(source.leftColumn(), source.rightColumn() + 1):
                    source_column = source.leftColumn() + ((column - source.leftColumn()) % pattern_width)
                    source_item = self.item(source_row, source_column)
                    self._set_cell_text(row, column, source_item.text() if source_item else "")

            self.clearSelection()
            self.setRangeSelected(
                QTableWidgetSelectionRange(source.topRow(), source.leftColumn(), self._fill_target_row, source.rightColumn()),
                True,
            )
            self.setCurrentCell(self._fill_target_row, source.rightColumn())

        self._run_tracked_operation("Riempimento celle", fill_action)

    def _set_text_in_range(self, selection_range: QTableWidgetSelectionRange, text: str) -> None:
        for row in range(selection_range.topRow(), selection_range.bottomRow() + 1):
            for column in range(selection_range.leftColumn(), selection_range.rightColumn() + 1):
                self._set_cell_text(row, column, text)

    def _set_cell_text(self, row: int, column: int, text: str) -> None:
        item = self.item(row, column)
        if item is None:
            item = make_table_item("")
            self.setItem(row, column, item)
        if not (item.flags() & Qt.ItemIsEditable):
            return
        item.setText(text)

    def _move_cell_value(self, source: tuple[int, int], target: tuple[int, int]) -> None:
        if source == target:
            return
        def move_action() -> None:
            source_item = self.item(*source)
            if source_item is None or not (source_item.flags() & Qt.ItemIsEditable):
                return
            target_item = self.item(*target)
            if target_item is None:
                target_item = make_table_item("")
                self.setItem(target[0], target[1], target_item)
            if not (target_item.flags() & Qt.ItemIsEditable):
                return
            target_item.setText(source_item.text())
            source_item.setText("")
            self.setCurrentCell(target[0], target[1])

        self._run_tracked_operation("Sposta contenuto", move_action)

    def snapshot_state(self) -> list[list[str]]:
        return [
            [self.item(row, column).text() if self.item(row, column) else "" for column in range(self.columnCount())]
            for row in range(self.rowCount())
        ]

    def restore_snapshot(self, snapshot: list[list[str]]) -> None:
        self._restoring_snapshot = True
        try:
            self.blockSignals(True)
            for row_index, row_values in enumerate(snapshot):
                if row_index >= self.rowCount():
                    break
                for column_index, value in enumerate(row_values):
                    if column_index >= self.columnCount():
                        break
                    item = self.item(row_index, column_index)
                    if item is None:
                        if value == "":
                            continue
                        item = make_table_item("")
                        self.setItem(row_index, column_index, item)
                    item.setText(value)
        finally:
            self.blockSignals(False)
            self._restoring_snapshot = False
            self._pending_edit_snapshot = None
            self._update_fill_handle()

    def _run_tracked_operation(self, label: str, action) -> None:
        before = self.snapshot_state()
        self._tracking_operation = True
        try:
            action()
        finally:
            self._tracking_operation = False
            self._pending_edit_snapshot = None
        after = self.snapshot_state()
        if after != before:
            self.operationCommitted.emit(before, after, label)

    def _handle_item_changed(self, item: QTableWidgetItem) -> None:
        if self._tracking_operation or self._restoring_snapshot:
            return
        if self._pending_edit_snapshot is None:
            return
        after = self.snapshot_state()
        before = self._pending_edit_snapshot
        self._pending_edit_snapshot = None
        if after != before:
            self.operationCommitted.emit(before, after, "Modifica cella")

    def _selection_range(self) -> QTableWidgetSelectionRange | None:
        ranges = self.selectedRanges()
        if ranges:
            return ranges[0]
        current_row = self.currentRow()
        current_column = self.currentColumn()
        if current_row < 0 or current_column < 0:
            return None
        return QTableWidgetSelectionRange(current_row, current_column, current_row, current_column)

    def _editable_selection_range(self) -> QTableWidgetSelectionRange | None:
        selection_range = self._selection_range()
        if selection_range is None:
            return None
        for row in range(selection_range.topRow(), selection_range.bottomRow() + 1):
            for column in range(selection_range.leftColumn(), selection_range.rightColumn() + 1):
                item = self.item(row, column)
                if item is None or not (item.flags() & Qt.ItemIsEditable):
                    return None
        return selection_range

    def _update_fill_handle(self) -> None:
        if self._fill_dragging:
            return
        selection_range = self._editable_selection_range()
        if selection_range is None:
            self._fill_handle.hide()
            return
        bottom_right_index = self.model().index(selection_range.bottomRow(), selection_range.rightColumn())
        rect = self.visualRect(bottom_right_index)
        if not rect.isValid():
            self._fill_handle.hide()
            return
        handle_x = rect.right() - (self._fill_handle.width() // 2)
        handle_y = rect.bottom() - (self._fill_handle.height() // 2)
        self._fill_handle.move(QPoint(handle_x, handle_y))
        self._fill_handle.show()
        self._fill_handle.raise_()


class FocusTracker(QObject):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def eventFilter(self, watched, event):
        if isinstance(watched, QTableWidget) and event.type() in (QEvent.FocusIn, QEvent.MouseButtonPress):
            self.callback(watched)
        return super().eventFilter(watched, event)


class SummaryCard(QFrame):
    def __init__(self, title: str, value: str):
        super().__init__()
        self.title_label = QLabel(title)
        self.value_label = QLabel(value)

        self.title_label.setObjectName("cardTitle")
        self.value_label.setObjectName("cardValue")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        self.setObjectName("summaryCard")

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class HomePage(QWidget):
    contentChanged = Signal()

    def __init__(self):
        super().__init__()
        self.pdf_title_edit = QLineEdit()
        self.week_label_edit = QLineEdit()
        self.signature_edit = QLineEdit()
        self.path_label = QLabel()
        self.week_buttons: dict[int, QPushButton] = {}
        self._selected_week_number: int | None = None
        self._syncing_week_label = False
        self.cards = {
            "departments": SummaryCard("Reparti", "0"),
            "people": SummaryCard("Nominativi", "0"),
            "weekend_rows": SummaryCard("Righe weekend", "0"),
        }

        self.pdf_title_edit.setPlaceholderText(DEFAULT_WEEKLY_PDF_TITLE)
        self.week_label_edit.setPlaceholderText("Week: 14 da Lunedi 30/03/2026 a Sabato 04/04/2026")
        self.signature_edit.setPlaceholderText("Firma il responsabile")
        self.path_label.setObjectName("pathLabel")
        self.path_label.setWordWrap(True)

        pdf_panel = QFrame()
        pdf_panel.setObjectName("pdfPanel")
        pdf_layout = QGridLayout(pdf_panel)
        pdf_layout.setContentsMargins(18, 18, 18, 18)
        pdf_layout.setHorizontalSpacing(16)
        pdf_layout.setVerticalSpacing(10)
        pdf_title = QLabel("Testi PDF settimana")
        pdf_title.setObjectName("sectionTitle")
        pdf_help = QLabel("Qui modifichi il titolo grande del PDF e la riga sotto con Week 14...")
        pdf_help.setWordWrap(True)
        pdf_layout.addWidget(pdf_title, 0, 0, 1, 2)
        pdf_layout.addWidget(pdf_help, 1, 0, 1, 2)
        pdf_layout.addWidget(QLabel("Titolo PDF settimana"), 2, 0)
        pdf_layout.addWidget(self.pdf_title_edit, 2, 1)
        pdf_layout.addWidget(QLabel("Riga Week / sottotitolo"), 3, 0)
        pdf_layout.addWidget(self.week_label_edit, 3, 1)

        week_picker = QFrame()
        week_picker.setObjectName("pdfPanel")
        week_picker_layout = QVBoxLayout(week_picker)
        week_picker_layout.setContentsMargins(18, 18, 18, 18)
        week_picker_layout.setSpacing(12)
        week_picker_title = QLabel("Scelta settimana 2026")
        week_picker_title.setObjectName("sectionTitle")
        week_picker_help = QLabel("Clicca una week da 01 a 52. Il sottotitolo si aggiorna con l'intervallo Lunedi-Sabato del 2026.")
        week_picker_help.setWordWrap(True)
        week_picker.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        week_picker_layout.addWidget(week_picker_title)
        week_picker_layout.addWidget(week_picker_help)

        week_grid = QGridLayout()
        week_grid.setHorizontalSpacing(12)
        week_grid.setVerticalSpacing(12)
        for week_number in range(1, WEEK_SELECTOR_COUNT + 1):
            button = QPushButton(f"{week_number:02d}")
            button.setObjectName("weekButton")
            button.setCheckable(True)
            button.setMinimumSize(56, 38)
            button.setMaximumWidth(64)
            button.clicked.connect(lambda checked=False, number=week_number: self._handle_week_button_clicked(number))
            self.week_buttons[week_number] = button
            row = (week_number - 1) // 8
            column = (week_number - 1) % 8
            week_grid.addWidget(button, row, column)
        week_picker_layout.addLayout(week_grid)

        form_layout = QGridLayout()
        form_layout.setHorizontalSpacing(16)
        form_layout.setVerticalSpacing(12)
        form_layout.addWidget(QLabel("Percorso file"), 0, 0)
        form_layout.addWidget(self.path_label, 0, 1)
        form_layout.addWidget(QLabel("Firma responsabile"), 1, 0)
        form_layout.addWidget(self.signature_edit, 1, 1)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)
        for card in self.cards.values():
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            cards_layout.addWidget(card)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 22, 22, 22)
        hero_layout.setSpacing(18)
        hero_logo = QLabel()
        if APP_LOGO_PATH.exists():
            hero_logo.setPixmap(QPixmap(str(APP_LOGO_PATH)).scaled(112, 112, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        hero_text = QVBoxLayout()
        hero_text.setSpacing(10)
        hero_text.addWidget(QLabel("Pannello generale"))
        hero_text.addWidget(
            QLabel(
                "Apri il file Excel, aggiorna i turni nei pannelli dedicati, salva con backup e genera i PDF ufficiali per settimana, sabato, domenica e portineria."
            )
        )
        hero_layout.addWidget(hero_logo, 0, Qt.AlignTop)
        hero_layout.addLayout(hero_text, 1)

        content_widget = QWidget()
        root_layout = QVBoxLayout(content_widget)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)
        root_layout.addWidget(hero)
        root_layout.addWidget(pdf_panel)
        root_layout.addWidget(week_picker)
        root_layout.addLayout(cards_layout)
        root_layout.addLayout(form_layout)
        root_layout.addStretch(1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidget(content_widget)

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll_area)

        self.pdf_title_edit.textChanged.connect(self.contentChanged)
        self.week_label_edit.textChanged.connect(self.contentChanged)
        self.week_label_edit.textChanged.connect(self._handle_week_label_changed)
        self.week_label_edit.editingFinished.connect(self._normalize_week_label_from_text)
        self.signature_edit.textChanged.connect(self.contentChanged)

    def set_data(self, *, workbook_path: Path, summary: dict[str, object], pdf_title: str) -> None:
        self.path_label.setText(str(workbook_path))
        self.pdf_title_edit.blockSignals(True)
        self.week_label_edit.blockSignals(True)
        self.signature_edit.blockSignals(True)
        self.pdf_title_edit.setText(pdf_title)
        self.week_label_edit.setText(str(summary["week"]))
        self.signature_edit.setText(str(summary["signature"]))
        self.pdf_title_edit.blockSignals(False)
        self.week_label_edit.blockSignals(False)
        self.signature_edit.blockSignals(False)
        self.cards["departments"].set_value(str(summary["departments"]))
        self.cards["people"].set_value(str(summary["people"]))
        self.cards["weekend_rows"].set_value(str(summary["weekend_rows"]))
        self._handle_week_label_changed(self.week_label_edit.text())

    def pdf_title(self) -> str:
        return self.pdf_title_edit.text().strip() or DEFAULT_WEEKLY_PDF_TITLE

    def week_label(self) -> str:
        return self.week_label_edit.text().strip()

    def signature(self) -> str:
        return self.signature_edit.text().strip()

    def _handle_week_button_clicked(self, week_number: int) -> None:
        self._selected_week_number = week_number
        self._update_week_button_states()
        self._syncing_week_label = True
        self.week_label_edit.setText(_format_week_label_from_number(week_number))
        self._syncing_week_label = False

    def _handle_week_label_changed(self, text: str) -> None:
        if self._syncing_week_label:
            return
        self._selected_week_number = _infer_week_number_from_text(text)
        self._update_week_button_states()

    def _normalize_week_label_from_text(self) -> None:
        week_number = _infer_week_number_from_text(self.week_label_edit.text())
        if week_number is None:
            return
        normalized = _format_week_label_from_number(week_number)
        if self.week_label_edit.text().strip() == normalized:
            return
        self._syncing_week_label = True
        self.week_label_edit.setText(normalized)
        self._syncing_week_label = False
        self._selected_week_number = week_number
        self._update_week_button_states()

    def _update_week_button_states(self) -> None:
        for week_number, button in self.week_buttons.items():
            button.blockSignals(True)
            button.setChecked(week_number == self._selected_week_number)
            button.blockSignals(False)


class WeeklyEditor(QWidget):
    contentChanged = Signal()

    def __init__(self):
        super().__init__()
        self.table = SpreadsheetTableWidget()
        self.headers: list[str] = []
        self.sections: list[WeeklySectionData] = []
        self._loading = False

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(24, 24, 24, 24)
        self.root_layout.setSpacing(16)

        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setAlternatingRowColors(False)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._handle_table_change)
        self.table.itemSelectionChanged.connect(lambda: self._set_active_table(self.table))

    def set_data(self, headers: list[str], sections: list[WeeklySectionData]) -> None:
        self.headers = headers
        self.sections = sections
        self._loading = True
        self._clear_layout()

        intro = QLabel(
            "Compilazione settimana: cambia i reparti nella fascia alta, poi compila direttamente le tre righe del turno. "
            "Puoi modificare anche gli orari blu se ti serve correggerli."
        )
        intro.setWordWrap(True)
        self.root_layout.addWidget(intro)
        self._configure_weekly_table(headers, sections)
        self.root_layout.addWidget(self.table)
        self._loading = False

    def export_values(self) -> list[list[list[str]]]:
        exported: list[list[list[str]]] = []
        for section_index in range(len(self.sections)):
            section_rows = [["" for _ in range(len(self.headers))] for _ in range(3)]
            for row_offset in range(3):
                table_row = self._section_data_row(section_index, row_offset)
                for column_index in WEEKLY_ALL_COLUMN_INDEXES:
                    item = self.table.item(table_row, column_index + 1)
                    section_rows[row_offset][column_index] = item.text().strip() if item else ""
            exported.append(section_rows)
        return exported

    def export_headers(self) -> list[str]:
        values = ["" for _ in range(len(self.headers))]
        for column_index in WEEKLY_ALL_COLUMN_INDEXES:
            item = self.table.item(1, column_index + 1)
            values[column_index] = item.text().strip() if item else ""
        return values

    def export_time_values(self) -> list[list[str]]:
        values: list[list[str]] = []
        for section_index in range(len(self.sections)):
            section_time_values: list[str] = []
            for column_index in WEEKLY_ALL_COLUMN_INDEXES:
                item = self.table.item(self._section_time_row(section_index), column_index + 1)
                section_time_values.append(item.text().strip() if item else "")
            values.append(section_time_values)
        return values

    def apply_text_to_selection(self, text: str, fill_empty_only: bool = False) -> bool:
        selected_items = self.table.selectedItems()
        if not selected_items:
            return False
        self._loading = True
        for item in selected_items:
            if not (item.flags() & Qt.ItemIsEditable):
                continue
            if fill_empty_only and item.text().strip():
                continue
            item.setText(text)
        self._loading = False
        self.contentChanged.emit()
        return True

    def clear_selection(self) -> bool:
        return self.apply_text_to_selection("")

    def register_focus_tracker(self, tracker: FocusTracker) -> None:
        if not self.table.property("focusTrackerInstalled"):
            self.table.installEventFilter(tracker)
            self.table.setProperty("focusTrackerInstalled", True)

    def _handle_table_change(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        if item.row() == 1 and item.column() > 0:
            self._sync_header_column(item.column(), item.text())
        self.contentChanged.emit()

    def _set_active_table(self, table: QTableWidget) -> None:
        return

    @staticmethod
    def _make_reparto_tag(value: str) -> QTableWidgetItem:
        item = make_table_item(value)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item.setBackground(QColor("#DCEBFF"))
        item.setForeground(QColor("#16315C"))
        return item

    @staticmethod
    def _make_static_item(value: str) -> QTableWidgetItem:
        item = make_table_item(value)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item.setBackground(QColor("#EEF5FF"))
        item.setForeground(QColor("#16315C"))
        return item

    @staticmethod
    def _make_header_item(value: str) -> QTableWidgetItem:
        item = make_table_item(value)
        item.setBackground(QColor("#DCEBFF"))
        item.setForeground(QColor("#16315C"))
        return item

    @staticmethod
    def _make_time_item(value: str) -> QTableWidgetItem:
        item = make_table_item(value)
        item.setBackground(QColor("#2F61C8"))
        item.setForeground(QColor("#FFFFFF"))
        return item

    @staticmethod
    def _make_shift_label_item(value: str) -> QTableWidgetItem:
        item = make_table_item(value)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item.setBackground(QColor("#C7DCFF"))
        item.setForeground(QColor("#16315C"))
        return item

    @staticmethod
    def _make_accent_body_item(value: str) -> QTableWidgetItem:
        item = make_table_item(value)
        item.setBackground(QColor("#DCEBFF"))
        item.setForeground(QColor("#16315C"))
        return item

    def _configure_weekly_table(self, headers: list[str], sections: list[WeeklySectionData]) -> None:
        self.table.clear()
        self.table.setColumnCount(11)
        total_rows = 18 if len(sections) >= 4 else 2 + (len(sections) * 4)
        if len(sections) >= 4:
            total_rows = 19
        self.table.setRowCount(total_rows)
        self.table.setColumnWidth(0, 52)
        for column in range(1, 11):
            self.table.setColumnWidth(column, 110 if column not in (6, 8) else 132)

        if len(sections) >= 4:
            heights = [22, 62, 30, 40, 40, 40, 30, 40, 40, 40, 30, 40, 40, 40, 30, 40, 40, 40, 40]
        else:
            heights = [22, 62] + ([30, 40, 40, 40] * len(sections))
        for row_index, height in enumerate(heights):
            self.table.setRowHeight(row_index, height)

        self.table.setItem(0, 0, self._make_static_item(""))
        self.table.setItem(1, 0, self._make_shift_label_item("TURNO"))
        self.table.setSpan(1, 0, total_rows - 1, 1)

        for column_index, header in enumerate(headers, start=1):
            self.table.setItem(0, column_index, self._make_reparto_tag("REPARTO"))
            self.table.setItem(1, column_index, self._make_header_item(header))

        for section_index, section in enumerate(sections):
            start_row = self._section_time_row(section_index)
            self.table.setItem(start_row, 0, self._make_static_item(""))
            for column_index, value in enumerate(section.time_values, start=1):
                self.table.setItem(start_row, column_index, self._make_time_item(value))

            label = f"{section_index + 1}°"
            for data_row_offset, row_values in enumerate(section.rows):
                table_row = self._section_data_row(section_index, data_row_offset)
                self.table.setItem(table_row, 0, self._make_shift_label_item(label))
                for column_index, value in enumerate(row_values, start=1):
                    if section_index == 2 and data_row_offset == 2:
                        self.table.setItem(table_row, column_index, self._make_accent_body_item(value))
                    else:
                        self.table.setItem(table_row, column_index, make_table_item(value))

        self.table.setMinimumHeight(900 if len(sections) >= 4 else 710)

    def _sync_header_column(self, table_column: int, text: str) -> None:
        self._loading = True
        item = self.table.item(1, table_column)
        if item is None:
            self.table.setItem(1, table_column, self._make_header_item(text))
        else:
            item.setText(text)
        self._loading = False

    @staticmethod
    def _section_start_row(section_index: int) -> int:
        return 2 + (section_index * 4)

    @staticmethod
    def _section_time_row(section_index: int) -> int:
        if section_index == 0:
            return 2
        if section_index == 1:
            return 6
        if section_index == 2:
            return 10
        if section_index == 3:
            return 15
        return 2 + (section_index * 4)

    @staticmethod
    def _section_data_row(section_index: int, row_offset: int) -> int:
        custom_rows = {
            0: [3, 4, 5],
            1: [7, 8, 9],
            2: [11, 12, 14],
            3: [16, 17, 18],
        }
        if section_index in custom_rows:
            return custom_rows[section_index][row_offset]
        return WeeklyEditor._section_start_row(section_index) + 1 + row_offset

    def _clear_layout(self) -> None:
        while self.root_layout.count():
            item = self.root_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                if widget is self.table:
                    self.root_layout.removeWidget(self.table)
                else:
                    widget.deleteLater()


class WeekendEditor(QWidget):
    contentChanged = Signal()

    def __init__(self, title: str):
        super().__init__()
        self.sheet_name = ""
        self.base_date_edit = QLineEdit()
        self.table = SpreadsheetTableWidget()
        self._loading = False

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")

        self.base_date_edit.setPlaceholderText("27/03/2026 oppure 2026-03-27")

        meta_layout = QGridLayout()
        meta_layout.addWidget(QLabel("Data base C4"), 0, 0)
        meta_layout.addWidget(self.base_date_edit, 0, 1)

        self.table.setColumnCount(len(WEEKEND_COLUMN_LABELS))
        self.table.setHorizontalHeaderLabels(list(WEEKEND_COLUMN_LABELS))
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(16)
        root_layout.addWidget(title_label)
        root_layout.addLayout(meta_layout)
        root_layout.addWidget(self.table)

        self.base_date_edit.textChanged.connect(self._handle_base_date_change)
        self.table.itemChanged.connect(self._emit_change)

    def set_data(self, sheet: WeekendSheetData) -> None:
        self.sheet_name = sheet.name
        self._loading = True
        self.base_date_edit.blockSignals(True)
        self.base_date_edit.setText(sheet.base_date.display)
        self.base_date_edit.blockSignals(False)
        self.table.clearContents()
        self.table.setRowCount(len(sheet.rows))
        for row_index, row in enumerate(sheet.rows):
            self.table.setVerticalHeaderItem(row_index, QTableWidgetItem(str(row.row_number)))
            for column_index, cell in enumerate(row.cells):
                self.table.setItem(row_index, column_index, make_table_item(cell.display))
        self._loading = False

    def reset_empty_data(self, sheet_name: str, row_count: int = PORTINERIA_WEEKEND_ROW_COUNT, base_date: str = "") -> None:
        self.sheet_name = sheet_name
        self._loading = True
        self.base_date_edit.blockSignals(True)
        self.base_date_edit.setText(base_date)
        self.base_date_edit.blockSignals(False)
        self.table.clearContents()
        self.table.setRowCount(row_count)
        for row_index in range(row_count):
            self.table.setVerticalHeaderItem(row_index, QTableWidgetItem(str(row_index + 6)))
            for column_index in range(self.table.columnCount()):
                self.table.setItem(row_index, column_index, make_table_item(""))
        self._loading = False

    def export_rows(self) -> list[list[str]]:
        rows: list[list[str]] = []
        for row_index in range(self.table.rowCount()):
            row_values: list[str] = []
            for column_index in range(self.table.columnCount()):
                item = self.table.item(row_index, column_index)
                row_values.append(item.text().strip() if item else "")
            rows.append(row_values)
        return rows

    def base_date(self) -> str:
        return self.base_date_edit.text().strip()

    def apply_text_to_selection(self, text: str, fill_empty_only: bool = False) -> bool:
        selected_items = self.table.selectedItems()
        if not selected_items:
            return False
        self._loading = True
        for item in selected_items:
            if fill_empty_only and item.text().strip():
                continue
            item.setText(text)
        self._loading = False
        self.contentChanged.emit()
        return True

    def clear_selection(self) -> bool:
        return self.apply_text_to_selection("")

    def register_focus_tracker(self, tracker: FocusTracker) -> None:
        if not self.table.property("focusTrackerInstalled"):
            self.table.installEventFilter(tracker)
            self.table.setProperty("focusTrackerInstalled", True)

    def _emit_change(self) -> None:
        if not self._loading:
            self.contentChanged.emit()

    def _handle_base_date_change(self) -> None:
        if self._loading:
            return
        self._autofill_dates_from_base_date()
        self.contentChanged.emit()

    def _autofill_dates_from_base_date(self) -> None:
        base_date = self._parse_date(self.base_date_edit.text())
        if base_date is None:
            return

        if "sabato" in self.sheet_name.lower():
            target_date = base_date + timedelta(days=1)
        elif "domenica" in self.sheet_name.lower():
            target_date = base_date + timedelta(days=2)
        else:
            target_date = base_date

        formatted = target_date.strftime("%d/%m/%Y")
        self._loading = True
        for row_index in range(self.table.rowCount()):
            has_other_values = False
            for column_index in range(1, self.table.columnCount()):
                item = self.table.item(row_index, column_index)
                if item and item.text().strip():
                    has_other_values = True
                    break
            if not has_other_values:
                continue

            item = self.table.item(row_index, 0)
            if item is None:
                item = make_table_item("")
                self.table.setItem(row_index, 0, item)
            item.setText(formatted)
        self._loading = False

    @staticmethod
    def _parse_date(text: str) -> datetime | None:
        clean = text.strip()
        if not clean:
            return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(clean, fmt)
            except ValueError:
                continue
        return None


class PortineriaWeeklyEditor(QWidget):
    contentChanged = Signal()

    def __init__(self):
        super().__init__()
        self.table = SpreadsheetTableWidget()
        self.sections = _default_portineria_sections()
        self._loading = False

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(24, 24, 24, 24)
        self.root_layout.setSpacing(16)

        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.table.setAlternatingRowColors(False)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._handle_table_change)
        self.reset_data()

    def reset_data(self) -> None:
        self.sections = _default_portineria_sections()
        self._loading = True
        self._clear_layout()

        intro = QLabel(
            "Settimana portineria: stessa compilazione della settimana, ma con la griglia semplificata "
            "del foglio di riferimento portineria."
        )
        intro.setWordWrap(True)
        self.root_layout.addWidget(intro)
        self._configure_table()
        self.root_layout.addWidget(self.table)
        self._loading = False

    def export_headers(self) -> list[str]:
        values: list[str] = []
        for table_column in PORTINERIA_DATA_COLUMNS:
            item = self.table.item(1, table_column)
            values.append(item.text().strip() if item else "")
        return values

    def export_sections(self) -> list[WeeklySectionData]:
        exported_sections: list[WeeklySectionData] = []
        for section_index, section in enumerate(self.sections):
            time_values: list[str] = []
            for table_column in PORTINERIA_DATA_COLUMNS:
                item = self.table.item(self._section_time_row(section_index), table_column)
                time_values.append(item.text().strip() if item else "")

            rows: list[list[str]] = []
            for row_offset in range(3):
                row_values: list[str] = []
                table_row = self._section_data_row(section_index, row_offset)
                for table_column in PORTINERIA_DATA_COLUMNS:
                    item = self.table.item(table_row, table_column)
                    row_values.append(item.text().strip() if item else "")
                rows.append(row_values)

            exported_sections.append(
                WeeklySectionData(
                    label=section.label,
                    time_label=time_values[0] if time_values else section.time_label,
                    time_values=time_values,
                    rows=rows,
                )
            )
        return exported_sections

    def apply_text_to_selection(self, text: str, fill_empty_only: bool = False) -> bool:
        selected_items = self.table.selectedItems()
        if not selected_items:
            return False
        self._loading = True
        for item in selected_items:
            if not (item.flags() & Qt.ItemIsEditable):
                continue
            if fill_empty_only and item.text().strip():
                continue
            item.setText(text)
        self._loading = False
        self.contentChanged.emit()
        return True

    def clear_selection(self) -> bool:
        return self.apply_text_to_selection("")

    def register_focus_tracker(self, tracker: FocusTracker) -> None:
        if not self.table.property("focusTrackerInstalled"):
            self.table.installEventFilter(tracker)
            self.table.setProperty("focusTrackerInstalled", True)

    def _handle_table_change(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        self.contentChanged.emit()

    def _configure_table(self) -> None:
        self.table.clear()
        self.table.setColumnCount(5)
        self.table.setRowCount(14)
        for column_index, width in enumerate((60, 220, 44, 170, 220)):
            self.table.setColumnWidth(column_index, width)
        for row_index, height in enumerate((22, 58, 30, 40, 40, 40, 30, 40, 40, 40, 30, 40, 40, 40)):
            self.table.setRowHeight(row_index, height)

        self.table.setItem(0, 0, WeeklyEditor._make_static_item(""))
        self.table.setItem(1, 0, WeeklyEditor._make_shift_label_item("TURNO"))
        self.table.setSpan(1, 0, 13, 1)

        self.table.setItem(0, 1, WeeklyEditor._make_reparto_tag("REPARTO"))
        self.table.setItem(0, 2, WeeklyEditor._make_static_item(""))
        self.table.setItem(0, 3, WeeklyEditor._make_reparto_tag("REPARTO"))
        self.table.setItem(0, 4, WeeklyEditor._make_reparto_tag("REPARTO"))

        for header_index, table_column in enumerate(PORTINERIA_DATA_COLUMNS):
            self.table.setItem(1, table_column, WeeklyEditor._make_header_item(PORTINERIA_HEADERS[header_index]))
        self.table.setItem(1, 2, WeeklyEditor._make_static_item(""))

        for section_index, section in enumerate(self.sections):
            time_row = self._section_time_row(section_index)
            self.table.setItem(time_row, 0, WeeklyEditor._make_static_item(""))
            self.table.setItem(time_row, 2, WeeklyEditor._make_static_item(""))
            for value_index, table_column in enumerate(PORTINERIA_DATA_COLUMNS):
                self.table.setItem(time_row, table_column, WeeklyEditor._make_time_item(section.time_values[value_index]))

            for row_offset, row_values in enumerate(section.rows):
                table_row = self._section_data_row(section_index, row_offset)
                shift_label = f"{section_index + 1}°" if row_offset > 0 else ""
                label_item = WeeklyEditor._make_shift_label_item(shift_label) if shift_label else WeeklyEditor._make_static_item("")
                self.table.setItem(table_row, 0, label_item)
                self.table.setItem(table_row, 2, WeeklyEditor._make_static_item(""))
                for value_index, table_column in enumerate(PORTINERIA_DATA_COLUMNS):
                    self.table.setItem(table_row, table_column, make_table_item(row_values[value_index]))

        self.table.setMinimumHeight(650)

    @staticmethod
    def _section_time_row(section_index: int) -> int:
        return 2 + (section_index * 4)

    @staticmethod
    def _section_data_row(section_index: int, row_offset: int) -> int:
        return PortineriaWeeklyEditor._section_time_row(section_index) + 1 + row_offset

    def _clear_layout(self) -> None:
        while self.root_layout.count():
            item = self.root_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                if widget is self.table:
                    self.root_layout.removeWidget(self.table)
                else:
                    widget.deleteLater()


class MainWindow(QMainWindow):
    def __init__(self, workbook_path: Path | None = None):
        super().__init__()
        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.workbook: TurniWorkbook | None = None
        self.is_dirty = False
        self.active_table: QTableWidget | None = None
        self._startup_workbook_path = workbook_path

        self.home_page = HomePage()
        self.weekly_page = WeeklyEditor()
        self.portineria_weekly_page = PortineriaWeeklyEditor()
        self.saturday_page = WeekendEditor("Comandata pulizie sabato")
        self.sunday_page = WeekendEditor("Comandata pulizie domenica")
        self.portineria_weekend_page = WeekendEditor("Weekend portineria")
        self.portineria_weekend_page.reset_empty_data("Weekend portineria")

        self.stack = QStackedWidget()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.weekly_page)
        self.stack.addWidget(self.portineria_weekly_page)
        self.stack.addWidget(self.saturday_page)
        self.stack.addWidget(self.sunday_page)
        self.stack.addWidget(self.portineria_weekend_page)

        self.nav_buttons: list[QPushButton] = []
        self.search_edit = QLineEdit()
        self.quick_value_edit = QLineEdit()
        self.people_list = QListWidget()
        self.people_completer = QCompleter(self)
        self.status = QStatusBar()
        self.focus_tracker = FocusTracker(self._set_active_table)
        self.main_toolbar: QToolBar | None = None
        self.undo_action: QAction | None = None
        self._last_table_undo: tuple[SpreadsheetTableWidget, list[list[str]], str] | None = None

        self.setWindowTitle(APP_NAME)
        self.resize(1580, 940)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        elif APP_LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_LOGO_PATH)))
        self.setStatusBar(self.status)
        self.people_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.people_completer.setFilterMode(Qt.MatchContains)
        self.people_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.quick_value_edit.setCompleter(self.people_completer)
        self._build_shell()
        self._build_toolbar()
        self._build_dock()
        self._apply_theme()
        self._wire_signals()
        self._restore_state()

        for table in (
            self.weekly_page.table,
            self.portineria_weekly_page.table,
            self.saturday_page.table,
            self.sunday_page.table,
            self.portineria_weekend_page.table,
        ):
            table.operationCommitted.connect(self._store_last_undo)

    def load_startup_workbook(self) -> None:
        startup_path = self._startup_workbook_path
        if startup_path is None:
            last_path = self.settings.value("lastWorkbook", "", str)
            if last_path and Path(last_path).exists():
                startup_path = Path(last_path)
        if startup_path is None:
            self.status.showMessage("App pronta", 3000)
            return
        self.status.showMessage("Caricamento workbook in corso...", 5000)
        self.open_workbook(startup_path)

    def closeEvent(self, event) -> None:
        if not self._confirm_discard_if_needed():
            event.ignore()
            return
        normal_geometry = self.normalGeometry()
        self.settings.setValue("windowMaximized", self.isMaximized())
        self.settings.setValue("windowX", normal_geometry.x())
        self.settings.setValue("windowY", normal_geometry.y())
        self.settings.setValue("windowWidth", normal_geometry.width())
        self.settings.setValue("windowHeight", normal_geometry.height())
        super().closeEvent(event)

    def open_workbook(self, path: Path | None = None) -> None:
        previous_path = self.workbook.path if self.workbook is not None else None
        if path is None:
            start_dir = self.settings.value("lastDirectory", str(Path.home()), str)
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Apri file turni",
                start_dir,
                "Excel (*.xlsx *.xlsm)",
            )
            if not file_name:
                return
            path = Path(file_name)

        if not path.exists():
            QMessageBox.warning(self, APP_NAME, "Il file selezionato non esiste piu.")
            return

        if not self._confirm_discard_if_needed():
            return

        try:
            workbook = TurniWorkbook(path)
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Impossibile aprire il workbook.\n\n{exc}")
            return

        self.workbook = workbook
        if previous_path != path:
            self.portineria_weekly_page.reset_data()
            self.portineria_weekend_page.reset_empty_data("Weekend portineria")
        self._clear_last_undo()
        self.settings.setValue("lastWorkbook", str(path))
        self.settings.setValue("lastDirectory", str(path.parent))
        self._refresh_ui()
        self._show_page(0)
        self.is_dirty = False
        self._update_title()
        self.status.showMessage(f"Workbook aperto: {path}", 5000)

    def reload_workbook(self) -> None:
        if self.workbook is None:
            return
        if not self._confirm_discard_if_needed():
            return
        self.workbook.load()
        self._clear_last_undo()
        self._refresh_ui()
        self._show_page(0)
        self.is_dirty = False
        self._update_title()
        self.status.showMessage("Workbook ricaricato", 4000)

    def save_workbook(self, backup: bool = False) -> None:
        if self.workbook is None:
            return
        try:
            weekend_rows = {
                self.saturday_page.sheet_name: self.saturday_page.export_rows(),
                self.sunday_page.sheet_name: self.sunday_page.export_rows(),
            }
            weekend_base_dates = {
                self.saturday_page.sheet_name: self.saturday_page.base_date(),
                self.sunday_page.sheet_name: self.sunday_page.base_date(),
            }
            backup_path = self.workbook.save(
                week_label=self.home_page.week_label(),
                signature=self.home_page.signature(),
                department_headers=self.weekly_page.export_headers(),
                weekly_time_values=self.weekly_page.export_time_values(),
                weekly_sections=self.weekly_page.export_values(),
                weekend_values=weekend_rows,
                weekend_base_dates=weekend_base_dates,
                backup=backup,
            )
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Salvataggio non riuscito.\n\n{exc}")
            return

        self._refresh_ui()
        self._clear_last_undo()
        self.is_dirty = False
        self._update_title()
        if backup_path is not None:
            self.status.showMessage(f"Salvato con backup: {backup_path}", 7000)
        else:
            self.status.showMessage("Salvataggio completato", 4000)

    def export_weekly_pdf(self) -> None:
        if self.workbook is None:
            return
        output_dir = self._choose_pdf_output_dir()
        if output_dir is None:
            return
        try:
            pdf_path, exported_paths = export_weekly_outputs(
                output_dir,
                title_text=self.home_page.pdf_title(),
                week_label=self.home_page.week_label(),
                signature=self.home_page.signature(),
                headers=self.weekly_page.export_headers(),
                sections=self._current_weekly_sections_for_export(),
                logo_path=APP_LOGO_PATH,
            )
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Generazione PDF/JPG settimana non riuscita.\n\n{exc}")
            return
        self.status.showMessage(self._format_export_message("settimana", pdf_path, exported_paths), 7000)

    def export_portineria_weekly_pdf(self) -> None:
        if self.workbook is None:
            return
        output_dir = self._choose_pdf_output_dir()
        if output_dir is None:
            return
        self.export_portineria_weekly_pdf_to_dir(output_dir)

    def export_saturday_pdf(self) -> None:
        self._export_weekend_pdf(self.saturday_page, SATURDAY_PDF_NAME, SATURDAY_IMAGE_NAME, "Comandata pulizie sabato")

    def export_sunday_pdf(self) -> None:
        self._export_weekend_pdf(self.sunday_page, SUNDAY_PDF_NAME, SUNDAY_IMAGE_NAME, "Comandata pulizie domenica")

    def export_portineria_weekend_pdf(self) -> None:
        self._export_weekend_pdf(
            self.portineria_weekend_page,
            PORTINERIA_WEEKEND_PDF_NAME,
            PORTINERIA_WEEKEND_IMAGE_NAME,
            "Weekend portineria",
        )

    def export_all_pdfs(self) -> None:
        if self.workbook is None:
            return
        output_dir = self._choose_pdf_output_dir()
        if output_dir is None:
            return
        self.export_weekly_pdf_to_dir(output_dir)
        self.export_portineria_weekly_pdf_to_dir(output_dir)
        self.export_saturday_pdf_to_dir(output_dir)
        self.export_sunday_pdf_to_dir(output_dir)
        self.export_portineria_weekend_pdf_to_dir(output_dir)

    def export_weekly_pdf_to_dir(self, output_dir: Path) -> None:
        if self.workbook is None:
            return
        try:
            pdf_path, exported_paths = export_weekly_outputs(
                output_dir,
                title_text=self.home_page.pdf_title(),
                week_label=self.home_page.week_label(),
                signature=self.home_page.signature(),
                headers=self.weekly_page.export_headers(),
                sections=self._current_weekly_sections_for_export(),
                logo_path=APP_LOGO_PATH,
            )
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Generazione PDF/JPG settimana non riuscita.\n\n{exc}")
            return
        self.status.showMessage(self._format_export_message("settimana", pdf_path, exported_paths), 7000)

    def export_saturday_pdf_to_dir(self, output_dir: Path) -> None:
        self._export_weekend_pdf(self.saturday_page, SATURDAY_PDF_NAME, SATURDAY_IMAGE_NAME, "Comandata pulizie sabato", output_dir)

    def export_sunday_pdf_to_dir(self, output_dir: Path) -> None:
        self._export_weekend_pdf(self.sunday_page, SUNDAY_PDF_NAME, SUNDAY_IMAGE_NAME, "Comandata pulizie domenica", output_dir)

    def export_portineria_weekly_pdf_to_dir(self, output_dir: Path) -> None:
        if self.workbook is None:
            return
        try:
            pdf_path, exported_paths = export_weekly_outputs(
                output_dir,
                title_text=self.home_page.pdf_title(),
                week_label=self.home_page.week_label(),
                signature=self.home_page.signature(),
                headers=self.portineria_weekly_page.export_headers(),
                sections=self.portineria_weekly_page.export_sections(),
                logo_path=APP_LOGO_PATH,
                pdf_name=PORTINERIA_WEEKLY_PDF_NAME,
                image_name=PORTINERIA_WEEKLY_IMAGE_NAME,
                layout="portineria",
            )
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Generazione PDF/JPG settimana portineria non riuscita.\n\n{exc}")
            return
        self.status.showMessage(self._format_export_message("settimana portineria", pdf_path, exported_paths), 7000)

    def export_portineria_weekend_pdf_to_dir(self, output_dir: Path) -> None:
        self._export_weekend_pdf(
            self.portineria_weekend_page,
            PORTINERIA_WEEKEND_PDF_NAME,
            PORTINERIA_WEEKEND_IMAGE_NAME,
            "Weekend portineria",
            output_dir,
        )

    def _export_weekend_pdf(self, page: WeekendEditor, pdf_name: str, image_name: str, title: str, output_dir: Path | None = None) -> None:
        if self.workbook is None:
            return
        if output_dir is None:
            output_dir = self._choose_pdf_output_dir()
            if output_dir is None:
                return
        try:
            pdf_path, exported_paths = export_weekend_outputs(
                output_dir,
                pdf_name=pdf_name,
                image_name=image_name,
                data=WeekendExportData(
                    title=title,
                    authorization_date=page.base_date(),
                    rows=page.export_rows(),
                ),
                logo_path=APP_LOGO_PATH,
                cert_logo_path=WEEKEND_ANCIS_LOGO_PATH,
                anid_logo_path=WEEKEND_ANID_LOGO_PATH,
            )
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Generazione PDF/JPG non riuscita.\n\n{exc}")
            return
        self.status.showMessage(self._format_export_message(title, pdf_path, exported_paths), 7000)

    def _choose_pdf_output_dir(self) -> Path | None:
        if self.workbook is None:
            return None
        default_dir = self.settings.value(PDF_OUTPUT_DIR_SETTING, str(self.workbook.path.parent), str)
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Scegli la cartella dove salvare PDF e JPG",
            default_dir,
        )
        if not selected_dir:
            return None
        output_dir = Path(selected_dir)
        self.settings.setValue(PDF_OUTPUT_DIR_SETTING, str(output_dir))
        return output_dir

    def _current_weekly_sections_for_export(self) -> list[WeeklySectionData]:
        if self.workbook is None:
            return []
        current_sections = self.workbook.weekly_sections()
        edited_rows = self.weekly_page.export_values()
        edited_time_values = self.weekly_page.export_time_values()
        merged_sections: list[WeeklySectionData] = []
        for index, section in enumerate(current_sections):
            merged_sections.append(
                WeeklySectionData(
                    label=section.label,
                    time_label=edited_time_values[index][0] if edited_time_values[index] else section.time_label,
                    time_values=edited_time_values[index],
                    rows=edited_rows[index],
                )
            )
        return merged_sections

    def apply_quick_value(self, fill_empty_only: bool = False) -> None:
        page = self.stack.currentWidget()
        text = self.quick_value_edit.text().strip()
        if not text:
            return
        applied = False
        if hasattr(page, "apply_text_to_selection"):
            applied = page.apply_text_to_selection(text, fill_empty_only=fill_empty_only)
        if not applied:
            self.status.showMessage("Seleziona almeno una cella da aggiornare", 3000)

    def clear_selected_cells(self) -> None:
        page = self.stack.currentWidget()
        if hasattr(page, "clear_selection") and page.clear_selection():
            return
        self.status.showMessage("Seleziona almeno una cella da svuotare", 3000)

    def undo_last_change(self) -> None:
        if self._last_table_undo is None:
            self.status.showMessage("Nessuna modifica da annullare", 3000)
            return
        table, snapshot, label = self._last_table_undo
        table.restore_snapshot(snapshot)
        self._clear_last_undo()
        self._mark_dirty()
        self.status.showMessage(f"Annullata ultima modifica: {label}", 4000)

    def load_name_into_quick_value(self, item: QListWidgetItem) -> None:
        self.quick_value_edit.setText(item.text())

    def filter_people_list(self, text: str) -> None:
        for index in range(self.people_list.count()):
            item = self.people_list.item(index)
            item.setHidden(text.lower() not in item.text().lower())

    def _refresh_ui(self) -> None:
        if self.workbook is None:
            return
        summary = self.workbook.summary()
        pdf_title = self.settings.value("weeklyPdfTitle", DEFAULT_WEEKLY_PDF_TITLE, str)
        self.home_page.set_data(workbook_path=self.workbook.path, summary=summary, pdf_title=pdf_title)
        self.weekly_page.set_data(self.workbook.department_headers(), self.workbook.weekly_sections())

        weekend_sheets = {sheet.name: sheet for sheet in self.workbook.weekend_sheets()}
        self.saturday_page.set_data(weekend_sheets[self.saturday_page.sheet_name or "Comandata pulizie Sabato"])
        self.sunday_page.set_data(weekend_sheets[self.sunday_page.sheet_name or "Comandata pulizie Domenica"])

        for editor in (
            self.weekly_page,
            self.portineria_weekly_page,
            self.saturday_page,
            self.sunday_page,
            self.portineria_weekend_page,
        ):
            editor.register_focus_tracker(self.focus_tracker)

        self.people_list.clear()
        people_names = self.workbook.people_palette()
        self.people_completer.setModel(self.people_list.model())
        for person in people_names:
            self.people_list.addItem(person)
        self.weekly_page.table.set_completion_names(people_names)
        self.portineria_weekly_page.table.set_completion_names(people_names)
        self.saturday_page.table.set_completion_names(people_names)
        self.sunday_page.table.set_completion_names(people_names)
        self.portineria_weekend_page.table.set_completion_names(people_names)

    def _build_shell(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(18, 18, 18, 18)
        nav_layout.setSpacing(10)

        brand = QLabel("Turni Planner")
        brand.setObjectName("brandLabel")
        subtitle = QLabel("Workflow rapido su Excel")
        subtitle.setObjectName("brandSubLabel")
        logo_label = QLabel()
        logo_label.setObjectName("sidebarLogo")
        if APP_LOGO_PATH.exists():
            logo_label.setPixmap(QPixmap(str(APP_LOGO_PATH)).scaled(132, 132, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)
            nav_layout.addWidget(logo_label, 0, Qt.AlignCenter)
        nav_layout.addWidget(brand)
        nav_layout.addWidget(subtitle)

        for index, label in enumerate(("Dashboard", "Settimana", "Portineria settimana", "Sabato", "Domenica", "Portineria weekend")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, index=index: self._show_page(index))
            self.nav_buttons.append(button)
            nav_layout.addWidget(button)

        nav_layout.addStretch(1)

        nav_panel = QFrame()
        nav_panel.setObjectName("navPanel")
        nav_panel.setLayout(nav_layout)
        nav_panel.setFixedWidth(250)

        content_layout = QHBoxLayout(central)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(nav_panel)
        content_layout.addWidget(self.stack, 1)

        self._show_page(0)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Azioni")
        toolbar.setObjectName("mainActionsToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.main_toolbar = toolbar

        open_action = QAction("Apri", self)
        open_action.triggered.connect(lambda: self.open_workbook())
        toolbar.addAction(open_action)

        reload_action = QAction("Ricarica", self)
        reload_action.triggered.connect(self.reload_workbook)
        toolbar.addAction(reload_action)

        save_action = QAction("Salva", self)
        save_action.triggered.connect(self.save_workbook)
        toolbar.addAction(save_action)

        undo_action = QAction("Annulla", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.setEnabled(False)
        undo_action.triggered.connect(self.undo_last_change)
        self.addAction(undo_action)
        toolbar.addAction(undo_action)
        self.undo_action = undo_action

        backup_action = QAction("Salva con backup", self)
        backup_action.triggered.connect(lambda: self.save_workbook(backup=True))
        toolbar.addAction(backup_action)

        toolbar.addSeparator()

        weekly_pdf_action = QAction("PDF + JPG settimana", self)
        weekly_pdf_action.triggered.connect(self.export_weekly_pdf)
        toolbar.addAction(weekly_pdf_action)

        portineria_weekly_pdf_action = QAction("PDF + JPG settimana portineria", self)
        portineria_weekly_pdf_action.triggered.connect(self.export_portineria_weekly_pdf)
        toolbar.addAction(portineria_weekly_pdf_action)

        saturday_pdf_action = QAction("PDF + JPG sabato", self)
        saturday_pdf_action.triggered.connect(self.export_saturday_pdf)
        toolbar.addAction(saturday_pdf_action)

        sunday_pdf_action = QAction("PDF + JPG domenica", self)
        sunday_pdf_action.triggered.connect(self.export_sunday_pdf)
        toolbar.addAction(sunday_pdf_action)

        portineria_weekend_pdf_action = QAction("PDF + JPG weekend portineria", self)
        portineria_weekend_pdf_action.triggered.connect(self.export_portineria_weekend_pdf)
        toolbar.addAction(portineria_weekend_pdf_action)

        all_pdf_action = QAction("PDF + JPG tutti", self)
        all_pdf_action.triggered.connect(self.export_all_pdfs)
        toolbar.addAction(all_pdf_action)

    @staticmethod
    def _format_export_message(label: str, pdf_path: Path, exported_paths: list[Path]) -> str:
        if len(exported_paths) == 1:
            return f"Creati PDF e JPG {label}: {pdf_path.name}, {exported_paths[0].name}"
        return f"Creati PDF e {len(exported_paths)} JPG per {label} in {pdf_path.parent}"

    def _build_dock(self) -> None:
        dock = QDockWidget("Compilazione rapida", self)
        dock.setObjectName("quickDock")
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.quick_value_edit.setPlaceholderText("Testo veloce da applicare")
        self.search_edit.setPlaceholderText("Cerca nominativo")

        apply_button = QPushButton("Applica alla selezione")
        apply_empty_button = QPushButton("Riempi solo celle vuote")
        clear_button = QPushButton("Svuota selezione")
        scorrimento_button = QPushButton("Usa SCORRIMENTO")

        apply_button.clicked.connect(self.apply_quick_value)
        apply_empty_button.clicked.connect(lambda: self.apply_quick_value(fill_empty_only=True))
        clear_button.clicked.connect(self.clear_selected_cells)
        scorrimento_button.clicked.connect(lambda: self.quick_value_edit.setText("SCORRIMENTO"))

        self.people_list.itemClicked.connect(self.load_name_into_quick_value)
        self.people_list.itemDoubleClicked.connect(lambda _: self.apply_quick_value())
        self.search_edit.textChanged.connect(self.filter_people_list)
        self.quick_value_edit.textEdited.connect(lambda _: self.people_completer.complete())
        self.quick_value_edit.editingFinished.connect(self._complete_quick_value_if_unique)

        layout.addWidget(QLabel("Valore rapido"))
        layout.addWidget(self.quick_value_edit)
        layout.addWidget(apply_button)
        layout.addWidget(apply_empty_button)
        layout.addWidget(clear_button)
        layout.addWidget(scorrimento_button)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Nominativi trovati nel file"))
        layout.addWidget(self.search_edit)
        layout.addWidget(self.people_list, 1)

        dock.setWidget(panel)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _wire_signals(self) -> None:
        self.home_page.contentChanged.connect(self._mark_dirty)
        self.home_page.pdf_title_edit.textChanged.connect(lambda text: self.settings.setValue("weeklyPdfTitle", text or DEFAULT_WEEKLY_PDF_TITLE))
        self.weekly_page.contentChanged.connect(self._mark_dirty)
        self.portineria_weekly_page.contentChanged.connect(self._mark_dirty)
        self.saturday_page.contentChanged.connect(self._mark_dirty)
        self.sunday_page.contentChanged.connect(self._mark_dirty)
        self.portineria_weekend_page.contentChanged.connect(self._mark_dirty)

    def _store_last_undo(self, before: object, after: object, label: str) -> None:
        table = self.sender()
        if not isinstance(table, SpreadsheetTableWidget):
            return
        self._last_table_undo = (table, before, label)
        if self.undo_action is not None:
            self.undo_action.setEnabled(True)

    def _clear_last_undo(self) -> None:
        self._last_table_undo = None
        if self.undo_action is not None:
            self.undo_action.setEnabled(False)

    def _complete_quick_value_if_unique(self) -> None:
        text = self.quick_value_edit.text().strip()
        if not text or self.workbook is None:
            return
        matches = [name for name in self.workbook.people_palette() if text.lower() in name.lower()]
        if len(matches) == 1:
            self.quick_value_edit.setText(matches[0])

    def _restore_state(self) -> None:
        saved_layout_version = self.settings.value("windowLayoutVersion", 0, int)
        if saved_layout_version != WINDOW_LAYOUT_VERSION:
            self.settings.remove("geometry")
            self.settings.remove("windowState")
            self.settings.remove("windowMaximized")
            self.settings.remove("windowX")
            self.settings.remove("windowY")
            self.settings.remove("windowWidth")
            self.settings.remove("windowHeight")
            self.settings.setValue("windowLayoutVersion", WINDOW_LAYOUT_VERSION)
            return
        width = self.settings.value("windowWidth", 0, int)
        height = self.settings.value("windowHeight", 0, int)
        if width > 0 and height > 0:
            self.resize(width, height)

        x = self.settings.value("windowX", None)
        y = self.settings.value("windowY", None)
        if x is not None and y is not None and width > 0 and height > 0:
            target_rect = QRect(int(x), int(y), width, height)
            if self._is_rect_visible_on_any_screen(target_rect):
                self.move(target_rect.topLeft())

        if self.settings.value("windowMaximized", False, bool):
            self.setWindowState(self.windowState() | Qt.WindowMaximized)

        if self.main_toolbar is not None:
            self.addToolBar(Qt.TopToolBarArea, self.main_toolbar)
            self.main_toolbar.show()

    @staticmethod
    def _is_rect_visible_on_any_screen(rect: QRect) -> bool:
        for screen in QApplication.screens():
            available = screen.availableGeometry()
            if available.intersects(rect):
                return True
        return False

    def _show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)

    def _mark_dirty(self) -> None:
        self.is_dirty = True
        self._update_title()

    def _update_title(self) -> None:
        suffix = " *" if self.is_dirty else ""
        path_text = str(self.workbook.path) if self.workbook else "nessun file"
        self.setWindowTitle(f"{APP_NAME} - {path_text}{suffix}")

    def _confirm_discard_if_needed(self) -> bool:
        if not self.is_dirty:
            return True
        answer = QMessageBox.question(
            self,
            APP_NAME,
            "Ci sono modifiche non salvate. Vuoi scartarle?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def _set_active_table(self, table: QTableWidget) -> None:
        self.active_table = table

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        app.setStyle("Fusion")

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#f1f5f9"))
        palette.setColor(QPalette.WindowText, QColor("#0f172a"))
        palette.setColor(QPalette.Base, QColor("#ffffff"))
        palette.setColor(QPalette.AlternateBase, QColor("#eff6ff"))
        palette.setColor(QPalette.Text, QColor("#0f172a"))
        palette.setColor(QPalette.Button, QColor("#1d4ed8"))
        palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.Highlight, QColor("#1d4ed8"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        app.setPalette(palette)

        app.setFont(QFont("Segoe UI", 10))
        app.setStyleSheet(
            """
            QMainWindow { background: #f1f5f9; }
            QToolBar { background: #e8efff; border: none; spacing: 8px; padding: 8px 12px; }
            QToolButton { background: #1d4ed8; color: #ffffff; border-radius: 10px; padding: 8px 14px; }
            QToolButton:hover { background: #1e40af; }
            #navPanel { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #1d4ed8); color: #ffffff; }
            #brandLabel { font-size: 28px; font-weight: 700; color: #ffffff; }
            #brandSubLabel { color: rgba(255, 255, 255, 0.76); margin-bottom: 18px; }
            #navPanel QPushButton { text-align: left; padding: 12px 14px; border: none; border-radius: 12px; color: #eff6ff; background: transparent; }
            #navPanel QPushButton:checked { background: rgba(255, 255, 255, 0.16); color: #ffffff; font-weight: 600; }
            #navPanel QPushButton:hover:!checked { background: rgba(255, 255, 255, 0.08); }
            QDockWidget { titlebar-close-icon: none; titlebar-normal-icon: none; }
            QDockWidget::title { background: #e8efff; padding: 10px 12px; text-align: left; font-weight: 600; color: #1e3a8a; }
            QLabel#sectionTitle { font-size: 22px; font-weight: 700; }
            QLabel#subsectionLabel { font-size: 15px; font-weight: 700; color: #0f172a; margin-top: 6px; }
            #heroPanel { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:0.55 #1d4ed8, stop:1 #60a5fa); border-radius: 20px; color: #ffffff; }
            #heroPanel QLabel:first-child { font-size: 26px; font-weight: 700; }
            #pdfPanel { background: #ffffff; border: 1px solid #dbeafe; border-radius: 18px; }
            #summaryCard { background: #ffffff; border: 1px solid #dbeafe; border-radius: 18px; }
            #cardTitle { color: #475569; text-transform: uppercase; letter-spacing: 1px; font-size: 11px; }
            #cardValue { color: #0f172a; font-size: 26px; font-weight: 700; }
            #pathLabel { background: #ffffff; border: 1px solid #dbeafe; border-radius: 12px; padding: 12px; }
            QLineEdit, QListWidget, QTableWidget, QGroupBox { background: #ffffff; border: 1px solid #dbeafe; border-radius: 12px; }
            QLineEdit { padding: 10px 12px; }
            QListWidget { padding: 6px; }
            QListWidget::item { padding: 8px 10px; border-radius: 8px; }
            QListWidget::item:selected { background: #1d4ed8; color: #ffffff; }
            QPushButton { background: #1d4ed8; color: #ffffff; border: none; border-radius: 12px; padding: 10px 14px; font-weight: 600; }
            QPushButton:hover { background: #1e40af; }
            QPushButton#weekButton { background: #ffffff; color: #1e3a8a; border: 1px solid #bfdbfe; border-radius: 12px; padding: 8px 10px; font-weight: 700; }
            QPushButton#weekButton:hover:!checked { background: #eff6ff; border-color: #93c5fd; }
            QPushButton#weekButton:checked { background: #1d4ed8; color: #ffffff; border: 1px solid #1d4ed8; }
            QGroupBox { margin-top: 10px; padding-top: 18px; font-weight: 700; }
            QGroupBox::title { left: 14px; padding: 0 6px; }
            QHeaderView::section { background: #e8efff; border: none; border-right: 1px solid #bfdbfe; border-bottom: 1px solid #bfdbfe; padding: 8px; font-weight: 600; color: #1e3a8a; }
            QTableWidget { gridline-color: #dbeafe; selection-background-color: #1d4ed8; selection-color: #ffffff; }
            QStatusBar { background: #e8efff; color: #1e3a8a; }
            """
        )
