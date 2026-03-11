import sqlite3
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QInputDialog,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from preventivi_app.ai_service import (
    AIServiceError,
    API_KEY_SETTING,
    MODEL_SETTING,
    generate_quote_texts,
    get_configured_model,
    has_api_key,
)
from preventivi_app.database import (
    get_client_by_name,
    get_dashboard_counts,
    get_next_progressive_number,
    get_quote,
    get_quote_items,
    initialize_database,
    insert_quote,
    list_clients,
    list_quotes,
    update_excel_path,
    update_pdf_path,
    update_quote,
    update_quote_status,
    upsert_client,
)
from preventivi_app.excel_service import create_quote_excel, create_quotes_registry_excel
from preventivi_app.models import (
    PAYMENT_PAID,
    PAYMENT_PENDING,
    PAYMENT_STATUSES,
    QUOTE_CONFIRMED,
    QUOTE_STATUSES,
    QUOTE_TO_CONFIRM,
    QUOTE_WORK_DONE,
    ClientInput,
    QuoteInput,
    QuoteItemInput,
)
from preventivi_app.pdf_service import create_quote_pdf
from preventivi_app.settings_service import remove_setting, set_setting


STANDARD_INCLUDED_LINES = [
    "Tutte le attivita da svolgere come da sopralluogo",
    "Il costo del personale e incluso",
    "Il costo per oneri di sicurezza e interferenze e incluso",
    "Il costo del materiale di consumo e incluso",
    "Il tutto con nostro personale e attrezzature incluso",
    "Il costo per la piattaforma aerea e incluso",
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.selected_quote_id: Optional[int] = None
        self._updating_items_table = False
        self.setWindowTitle("Gestionale Preventivi")
        self.resize(1580, 900)
        self._build_ui()
        self.refresh_clients()
        self.refresh_quotes()
        self.reset_form()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(14)

        title = QLabel("Gestionale Preventivi")
        title.setStyleSheet("font-size: 26px; font-weight: bold;")
        subtitle = QLabel(
            "Anagrafica clienti, righe dettaglio, PDF, Excel e stati in un'unica schermata."
        )
        subtitle.setStyleSheet("color: #555;")

        header_row = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header_row.addLayout(title_block, 1)
        self.new_top_button = QPushButton("Nuovo")
        self.new_top_button.clicked.connect(self.reset_form)
        header_row.addWidget(self.new_top_button)
        main_layout.addLayout(header_row)

        dashboard_box = QGroupBox("Cruscotto")
        dashboard_layout = QGridLayout(dashboard_box)
        self.pending_label = QLabel("0")
        self.paid_label = QLabel("0")
        self.to_confirm_label = QLabel("0")
        self.confirmed_label = QLabel("0")
        self.work_done_label = QLabel("0")
        self._add_dashboard_item(dashboard_layout, 0, "Pending", self.pending_label)
        self._add_dashboard_item(dashboard_layout, 1, "Pagati", self.paid_label)
        self._add_dashboard_item(dashboard_layout, 2, "Da confermare", self.to_confirm_label)
        self._add_dashboard_item(dashboard_layout, 3, "Confermati", self.confirmed_label)
        self._add_dashboard_item(dashboard_layout, 4, "Lavori fatti", self.work_done_label)
        main_layout.addWidget(dashboard_box)

        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setSpacing(12)
        left_layout.addWidget(self._build_client_box())
        left_layout.addWidget(self._build_quote_box())
        left_layout.addWidget(self._build_items_box())
        left_layout.addWidget(self._build_ai_box())
        left_layout.addWidget(self._build_actions_box())
        left_layout.addStretch(1)
        left_column.setMinimumWidth(620)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        left_scroll.setWidget(left_column)

        right_panel = self._build_table_box()
        right_panel.setMinimumWidth(700)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_scroll)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([660, 900])

        main_layout.addWidget(splitter, 1)

        self.setCentralWidget(central_widget)

    def _add_dashboard_item(self, layout: QGridLayout, column: int, title: str, value_label: QLabel) -> None:
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(label, 0, column)
        layout.addWidget(value_label, 1, column)

    def _build_client_box(self) -> QGroupBox:
        box = QGroupBox("Cliente")
        layout = QVBoxLayout(box)

        selector_row = QHBoxLayout()
        self.client_selector = QComboBox()
        self.client_selector.setEditable(True)
        self.client_selector.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        load_client_button = QPushButton("Carica cliente")
        save_client_button = QPushButton("Salva anagrafica")
        load_client_button.clicked.connect(self.load_client_from_selector)
        save_client_button.clicked.connect(self.save_client_master)
        selector_row.addWidget(self.client_selector, 1)
        selector_row.addWidget(load_client_button)
        selector_row.addWidget(save_client_button)
        layout.addLayout(selector_row)

        form_layout = QFormLayout()
        self.client_contact_input = QLineEdit()
        self.client_email_input = QLineEdit()
        self.client_phone_input = QLineEdit()
        self.client_address_input = QTextEdit()
        self.client_address_input.setMinimumHeight(65)

        form_layout.addRow("Referente", self.client_contact_input)
        form_layout.addRow("Email", self.client_email_input)
        form_layout.addRow("Telefono", self.client_phone_input)
        form_layout.addRow("Indirizzo", self.client_address_input)
        layout.addLayout(form_layout)
        return box

    def _build_quote_box(self) -> QGroupBox:
        box = QGroupBox("Preventivo")
        layout = QFormLayout(box)

        self.progressive_value = QSpinBox()
        self.progressive_value.setMaximum(999999)
        self.progressive_value.setMinimum(1)
        self.offer_date_input = QLineEdit()
        self.recipient_attention_input = QLineEdit()
        self.work_site_input = QLineEdit()
        self.title_input = QLineEdit()
        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(90)
        self.opening_text_input = QTextEdit()
        self.opening_text_input.setMinimumHeight(90)
        self.included_items_input = QTextEdit()
        self.included_items_input.setMinimumHeight(110)
        self.add_standard_items_button = QPushButton("Aggiungi voci standard")
        self.add_standard_items_button.clicked.connect(self.add_standard_included_items)
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setMaximum(999999999.99)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix("EUR ")
        self.amount_hint = QLabel("L'importo offerta resta manuale. Le righe sono solo dettaglio del lavoro.")
        self.amount_hint.setStyleSheet("color: #555;")
        self.include_discount_note_input = QCheckBox("Aggiungi nota sconto 10% in fondo ai punti")
        self.payment_reference_input = QLineEdit()
        self.payment_status_input = QComboBox()
        self.payment_status_input.addItems(PAYMENT_STATUSES)
        self.quote_status_input = QComboBox()
        self.quote_status_input.addItems(QUOTE_STATUSES)
        self.notes_input = QTextEdit()
        self.notes_input.setMinimumHeight(70)
        self.closing_text_input = QLineEdit()
        self.signature_name_input = QLineEdit()

        layout.addRow("Numero", self.progressive_value)
        layout.addRow("Data offerta", self.offer_date_input)
        layout.addRow("C/A", self.recipient_attention_input)
        layout.addRow("Stabilimento / sede", self.work_site_input)
        layout.addRow("Oggetto", self.title_input)
        layout.addRow("Descrizione generale", self.description_input)
        layout.addRow("Testo introduttivo", self.opening_text_input)
        included_items_layout = QVBoxLayout()
        included_items_layout.addWidget(self.included_items_input)
        included_items_layout.addWidget(self.add_standard_items_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addRow("Punti inclusi", included_items_layout)
        layout.addRow("Importo", self.amount_input)
        layout.addRow("", self.amount_hint)
        layout.addRow("", self.include_discount_note_input)
        layout.addRow("PO pagamento", self.payment_reference_input)
        layout.addRow("Pagamento", self.payment_status_input)
        layout.addRow("Stato", self.quote_status_input)
        layout.addRow("Nota interna", self.notes_input)
        layout.addRow("Chiusura", self.closing_text_input)
        layout.addRow("Firma", self.signature_name_input)
        return box

    def _build_items_box(self) -> QGroupBox:
        box = QGroupBox("Righe preventivo")
        layout = QVBoxLayout(box)

        self.items_table = QTableWidget(0, 4)
        self.items_table.setMinimumHeight(180)
        self.items_table.setHorizontalHeaderLabels(
            ["Descrizione", "Quantita", "Prezzo unitario", "Totale"]
        )
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.itemChanged.connect(self.recalculate_items_total)
        layout.addWidget(self.items_table)

        button_row = QHBoxLayout()
        add_item_button = QPushButton("Aggiungi riga")
        remove_item_button = QPushButton("Rimuovi riga")
        add_item_button.clicked.connect(self.add_item_row)
        remove_item_button.clicked.connect(self.remove_selected_item_row)
        button_row.addWidget(add_item_button)
        button_row.addWidget(remove_item_button)
        button_row.addStretch(1)
        self.items_total_label = QLabel("Totale righe: EUR 0.00")
        self.items_total_label.setStyleSheet("font-weight: bold;")
        button_row.addWidget(self.items_total_label)
        layout.addLayout(button_row)
        return box

    def _build_ai_box(self) -> QGroupBox:
        box = QGroupBox("AI")
        layout = QVBoxLayout(box)

        self.ai_status_label = QLabel()
        self._refresh_ai_status_label()
        layout.addWidget(self.ai_status_label)

        first_row = QHBoxLayout()
        configure_button = QPushButton("Configura API key")
        remove_button = QPushButton("Rimuovi key")
        configure_button.clicked.connect(self.configure_ai)
        remove_button.clicked.connect(self.remove_ai_key)
        first_row.addWidget(configure_button)
        first_row.addWidget(remove_button)
        layout.addLayout(first_row)

        second_row = QHBoxLayout()
        opening_button = QPushButton("AI testo introduttivo")
        items_button = QPushButton("AI punti inclusi")
        both_button = QPushButton("AI genera tutto")
        opening_button.clicked.connect(lambda: self.generate_ai_content(mode="opening"))
        items_button.clicked.connect(lambda: self.generate_ai_content(mode="items"))
        both_button.clicked.connect(lambda: self.generate_ai_content(mode="both"))
        second_row.addWidget(opening_button)
        second_row.addWidget(items_button)
        second_row.addWidget(both_button)
        layout.addLayout(second_row)
        return box

    def _build_actions_box(self) -> QGroupBox:
        box = QGroupBox("Azioni")
        layout = QVBoxLayout(box)

        first_row = QHBoxLayout()
        save_button = QPushButton("Salva preventivo")
        refresh_button = QPushButton("Aggiorna elenco")
        save_button.clicked.connect(self.save_quote)
        refresh_button.clicked.connect(self.refresh_quotes)
        first_row.addWidget(save_button)
        first_row.addWidget(refresh_button)
        layout.addLayout(first_row)

        second_row = QHBoxLayout()
        pdf_button = QPushButton("Genera PDF")
        excel_button = QPushButton("Esporta Excel")
        registry_button = QPushButton("Registro Excel")
        pdf_button.clicked.connect(self.generate_pdf)
        excel_button.clicked.connect(self.generate_excel)
        registry_button.clicked.connect(self.export_registry_excel)
        second_row.addWidget(pdf_button)
        second_row.addWidget(excel_button)
        second_row.addWidget(registry_button)
        layout.addLayout(second_row)

        third_row = QHBoxLayout()
        mark_paid_button = QPushButton("Segna pagato")
        confirm_button = QPushButton("Conferma")
        work_done_button = QPushButton("Lavoro fatto")
        mark_paid_button.clicked.connect(lambda: self.update_selected_status(payment_status=PAYMENT_PAID))
        confirm_button.clicked.connect(lambda: self.update_selected_status(quote_status=QUOTE_CONFIRMED))
        work_done_button.clicked.connect(lambda: self.update_selected_status(quote_status=QUOTE_WORK_DONE))
        third_row.addWidget(mark_paid_button)
        third_row.addWidget(confirm_button)
        third_row.addWidget(work_done_button)
        layout.addLayout(third_row)
        return box

    def _build_table_box(self) -> QGroupBox:
        box = QGroupBox("Elenco preventivi")
        layout = QVBoxLayout(box)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Cerca"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Numero, cliente, email, telefono o oggetto")
        self.search_input.textChanged.connect(self.refresh_quotes)
        search_row.addWidget(self.search_input)
        self.payment_filter_input = QComboBox()
        self.payment_filter_input.addItem("Tutti", "")
        self.payment_filter_input.addItem("Pending", PAYMENT_PENDING)
        self.payment_filter_input.addItem("Pagati", PAYMENT_PAID)
        self.payment_filter_input.currentIndexChanged.connect(self.refresh_quotes)
        search_row.addWidget(QLabel("Pagamento"))
        search_row.addWidget(self.payment_filter_input)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Numero",
                "Cliente",
                "Referente",
                "Telefono",
                "Oggetto",
                "Importo",
                "PO",
                "Pagamento",
                "Stato",
                "Doc",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.load_selected_quote)
        self.table.setColumnHidden(0, True)
        layout.addWidget(self.table)
        return box

    def refresh_clients(self) -> None:
        current_text = self.client_selector.currentText().strip() if hasattr(self, "client_selector") else ""
        clients = list_clients()
        self.client_selector.blockSignals(True)
        self.client_selector.clear()
        self.client_selector.addItems([client["name"] for client in clients])
        self.client_selector.setCurrentText(current_text)
        self.client_selector.blockSignals(False)

    def refresh_quotes(self) -> None:
        rows = list_quotes(
            self.search_input.text(),
            self.payment_filter_input.currentData(),
        )
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            doc_status = []
            if row["pdf_path"]:
                doc_status.append("PDF")
            if row["excel_path"]:
                doc_status.append("XLSX")
            values = [
                str(row["id"]),
                str(row["progressive_number"]),
                row["client_name"],
                row["client_contact_person"],
                row["client_phone"],
                row["title"],
                f"EUR {row['amount']:.2f}",
                row["payment_reference"],
                row["payment_status"],
                row["quote_status"],
                ", ".join(doc_status) if doc_status else "-",
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column_index in (0, 1, 6, 8, 9, 10):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_index, column_index, item)

        self._refresh_dashboard()
        self._refresh_progressive_preview()

    def _refresh_dashboard(self) -> None:
        counts = get_dashboard_counts()
        self.pending_label.setText(str(counts["pending"]))
        self.paid_label.setText(str(counts["paid"]))
        self.to_confirm_label.setText(str(counts["to_confirm"]))
        self.confirmed_label.setText(str(counts["confirmed"]))
        self.work_done_label.setText(str(counts["work_done"]))

    def _refresh_progressive_preview(self) -> None:
        if self.selected_quote_id is None:
            self.progressive_value.setValue(get_next_progressive_number())

    def reset_form(self) -> None:
        self.selected_quote_id = None
        self.client_selector.setCurrentText("")
        self.client_contact_input.clear()
        self.client_email_input.clear()
        self.client_phone_input.clear()
        self.client_address_input.clear()
        self.offer_date_input.setText(self._default_offer_date())
        self.recipient_attention_input.clear()
        self.work_site_input.clear()
        self.title_input.clear()
        self.description_input.clear()
        self.opening_text_input.setPlainText(self._default_opening_text())
        self.included_items_input.setPlainText(self._default_included_items_text())
        self.amount_input.setValue(0.0)
        self.include_discount_note_input.setChecked(False)
        self.payment_reference_input.clear()
        self.payment_status_input.setCurrentText(PAYMENT_PENDING)
        self.quote_status_input.setCurrentText(QUOTE_TO_CONFIRM)
        self.notes_input.clear()
        self.closing_text_input.setText(self._default_closing_text())
        self.signature_name_input.setText(self._default_signature_name())
        self.items_table.setRowCount(0)
        self.table.clearSelection()
        self._update_items_total_label(0.0)
        self._refresh_progressive_preview()
        self._refresh_ai_status_label()

    def load_client_from_selector(self) -> None:
        client_row = get_client_by_name(self.client_selector.currentText())
        if client_row is None:
            self._show_warning("Cliente non trovato nell'anagrafica.")
            return

        self.client_selector.setCurrentText(client_row["name"])
        self.client_contact_input.setText(client_row["contact_person"])
        self.client_email_input.setText(client_row["email"])
        self.client_phone_input.setText(client_row["phone"])
        self.client_address_input.setPlainText(client_row["address"])

    def save_client_master(self) -> None:
        client_name = self.client_selector.currentText().strip()
        if not client_name:
            self._show_warning("Inserisci il nome del cliente.")
            return

        upsert_client(self._build_client_input())
        self.refresh_clients()
        self.client_selector.setCurrentText(client_name)
        self._show_info("Anagrafica cliente salvata.")

    def _build_client_input(self) -> ClientInput:
        return ClientInput(
            name=self.client_selector.currentText().strip(),
            contact_person=self.client_contact_input.text().strip(),
            email=self.client_email_input.text().strip(),
            phone=self.client_phone_input.text().strip(),
            address=self.client_address_input.toPlainText().strip(),
        )

    def add_item_row(self, description: str = "", quantity: float = 1.0, unit_price: float = 0.0) -> None:
        self._updating_items_table = True
        row_index = self.items_table.rowCount()
        self.items_table.insertRow(row_index)
        self.items_table.setItem(row_index, 0, QTableWidgetItem(description))
        self.items_table.setItem(row_index, 1, QTableWidgetItem(self._format_number(quantity)))
        self.items_table.setItem(row_index, 2, QTableWidgetItem(self._format_number(unit_price)))
        total_item = QTableWidgetItem(self._format_currency(quantity * unit_price))
        total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.items_table.setItem(row_index, 3, total_item)
        self._updating_items_table = False
        self.recalculate_items_total()

    def remove_selected_item_row(self) -> None:
        row_index = self.items_table.currentRow()
        if row_index < 0:
            self._show_warning("Seleziona una riga da rimuovere.")
            return
        self.items_table.removeRow(row_index)
        self.recalculate_items_total()

    def recalculate_items_total(self) -> None:
        if self._updating_items_table:
            return

        self._updating_items_table = True
        total_amount = 0.0
        for row_index in range(self.items_table.rowCount()):
            description_item = self.items_table.item(row_index, 0)
            quantity_item = self.items_table.item(row_index, 1)
            unit_price_item = self.items_table.item(row_index, 2)
            total_item = self.items_table.item(row_index, 3)

            description = description_item.text().strip() if description_item else ""
            quantity = self._parse_float(quantity_item.text() if quantity_item else "0")
            unit_price = self._parse_float(unit_price_item.text() if unit_price_item else "0")
            line_total = round(quantity * unit_price, 2)

            if total_item is None:
                total_item = QTableWidgetItem()
                total_item.setFlags(total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.items_table.setItem(row_index, 3, total_item)
            total_item.setText(self._format_currency(line_total))

            if description and quantity > 0 and unit_price >= 0:
                total_amount += line_total

        self._update_items_total_label(total_amount)

        self._updating_items_table = False

    def _update_items_total_label(self, total_amount: float) -> None:
        self.items_total_label.setText(f"Totale righe: {self._format_currency(total_amount)}")

    def collect_quote_items(self) -> list[QuoteItemInput]:
        items = []
        for row_index in range(self.items_table.rowCount()):
            description_item = self.items_table.item(row_index, 0)
            quantity_item = self.items_table.item(row_index, 1)
            unit_price_item = self.items_table.item(row_index, 2)

            description = description_item.text().strip() if description_item else ""
            quantity = self._parse_float(quantity_item.text() if quantity_item else "0")
            unit_price = self._parse_float(unit_price_item.text() if unit_price_item else "0")

            if not description and quantity == 0 and unit_price == 0:
                continue
            if not description:
                raise ValueError("Ogni riga deve avere una descrizione.")
            if quantity <= 0:
                raise ValueError("La quantita di ogni riga deve essere maggiore di zero.")
            if unit_price < 0:
                raise ValueError("Il prezzo unitario non puo essere negativo.")

            items.append(
                QuoteItemInput(
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                )
            )
        return items

    def collect_form_data(self) -> QuoteInput:
        client_name = self.client_selector.currentText().strip()
        offer_date = self.offer_date_input.text().strip()
        title = self.title_input.text().strip()
        description = self.description_input.toPlainText().strip()
        opening_text = self.opening_text_input.toPlainText().strip()
        included_items_text = self.included_items_input.toPlainText().strip()
        notes = self.notes_input.toPlainText().strip()
        items = self.collect_quote_items()
        amount = float(self.amount_input.value())

        if not client_name:
            raise ValueError("Inserisci il nome del cliente.")
        if not offer_date:
            raise ValueError("Inserisci la data dell'offerta.")
        if not title:
            raise ValueError("Inserisci l'oggetto del preventivo.")
        if not description and not items:
            raise ValueError("Inserisci una descrizione generale o almeno una riga dettaglio.")
        if amount <= 0:
            raise ValueError("L'importo deve essere maggiore di zero.")

        return QuoteInput(
            progressive_number=int(self.progressive_value.value()),
            client_name=client_name,
            client_contact_person=self.client_contact_input.text().strip(),
            client_email=self.client_email_input.text().strip(),
            client_phone=self.client_phone_input.text().strip(),
            client_address=self.client_address_input.toPlainText().strip(),
            offer_date=offer_date,
            recipient_attention=self.recipient_attention_input.text().strip(),
            work_site=self.work_site_input.text().strip(),
            title=title,
            description=description,
            opening_text=opening_text,
            included_items_text=included_items_text,
            amount=amount,
            payment_reference=self.payment_reference_input.text().strip(),
            payment_status=self.payment_status_input.currentText(),
            quote_status=self.quote_status_input.currentText(),
            notes=notes,
            closing_text=self.closing_text_input.text().strip(),
            signature_name=self.signature_name_input.text().strip(),
            include_discount_note=self.include_discount_note_input.isChecked(),
            items=items,
        )

    def save_quote(self) -> None:
        try:
            quote = self.collect_form_data()
        except ValueError as exc:
            self._show_warning(str(exc))
            return

        upsert_client(self._build_client_input())
        self.refresh_clients()

        try:
            if self.selected_quote_id is None:
                quote_id = insert_quote(quote)
                self.selected_quote_id = quote_id
                self._show_info("Preventivo creato correttamente.")
            else:
                update_quote(self.selected_quote_id, quote)
                quote_id = self.selected_quote_id
                self._show_info("Preventivo aggiornato correttamente.")
        except sqlite3.IntegrityError:
            self._show_warning("Il numero progressivo scelto e gia presente. Inseriscine uno diverso.")
            return

        self.refresh_quotes()
        self.select_quote_by_id(quote_id)

    def load_selected_quote(self) -> None:
        if self.table.currentRow() < 0:
            return

        quote_id_item = self.table.item(self.table.currentRow(), 0)
        if quote_id_item is None:
            return

        quote_id = int(quote_id_item.text())
        quote_row = get_quote(quote_id)
        if quote_row is None:
            return

        self.selected_quote_id = quote_id
        self.progressive_value.setValue(int(quote_row["progressive_number"]))
        self.client_selector.setCurrentText(quote_row["client_name"])
        self.client_contact_input.setText(quote_row["client_contact_person"])
        self.client_email_input.setText(quote_row["client_email"])
        self.client_phone_input.setText(quote_row["client_phone"])
        self.client_address_input.setPlainText(quote_row["client_address"])
        self.offer_date_input.setText(quote_row["offer_date"])
        self.recipient_attention_input.setText(quote_row["recipient_attention"])
        self.work_site_input.setText(quote_row["work_site"])
        self.title_input.setText(quote_row["title"])
        self.description_input.setPlainText(quote_row["description"])
        self.opening_text_input.setPlainText(quote_row["opening_text"])
        self.included_items_input.setPlainText(quote_row["included_items_text"])
        self.amount_input.setValue(float(quote_row["amount"]))
        self.include_discount_note_input.setChecked(bool(quote_row["include_discount_note"]))
        self.payment_reference_input.setText(quote_row["payment_reference"])
        self.payment_status_input.setCurrentText(quote_row["payment_status"])
        self.quote_status_input.setCurrentText(quote_row["quote_status"])
        self.notes_input.setPlainText(quote_row["notes"])
        self.closing_text_input.setText(quote_row["closing_text"])
        self.signature_name_input.setText(quote_row["signature_name"])
        self._populate_items_table(get_quote_items(quote_id))

    def _populate_items_table(self, item_rows) -> None:
        self._updating_items_table = True
        self.items_table.setRowCount(0)
        for item_row in item_rows:
            self.add_item_row(
                description=item_row["description"],
                quantity=float(item_row["quantity"]),
                unit_price=float(item_row["unit_price"]),
            )
        self._updating_items_table = False
        self.recalculate_items_total()

    def select_quote_by_id(self, quote_id: int) -> None:
        for row_index in range(self.table.rowCount()):
            item = self.table.item(row_index, 0)
            if item and int(item.text()) == quote_id:
                self.table.selectRow(row_index)
                break

    def update_selected_status(self, *, payment_status: Optional[str] = None, quote_status: Optional[str] = None) -> None:
        if self.selected_quote_id is None:
            self._show_warning("Seleziona prima un preventivo.")
            return

        payment_reference = None
        if payment_status == PAYMENT_PAID:
            payment_reference = self.payment_reference_input.text().strip()
            if not payment_reference:
                payment_reference, confirmed = QInputDialog.getText(
                    self,
                    "PO pagamento",
                    "Inserisci il PO o identificativo del pagamento:",
                )
                if not confirmed or not payment_reference.strip():
                    self._show_warning("Per segnare pagato devi inserire un PO.")
                    return
                payment_reference = payment_reference.strip()
                self.payment_reference_input.setText(payment_reference)

        update_quote_status(
            self.selected_quote_id,
            payment_status=payment_status,
            quote_status=quote_status,
            payment_reference=payment_reference,
        )

        if payment_status is not None:
            self.payment_status_input.setCurrentText(payment_status)
        if quote_status is not None:
            self.quote_status_input.setCurrentText(quote_status)

        self.refresh_quotes()
        self.select_quote_by_id(self.selected_quote_id)
        self._show_info("Stato aggiornato correttamente.")

    def generate_pdf(self) -> None:
        if self.selected_quote_id is None:
            self._show_warning("Salva o seleziona un preventivo prima di generare il PDF.")
            return

        quote_row = get_quote(self.selected_quote_id)
        if quote_row is None:
            self._show_warning("Preventivo non trovato.")
            return

        pdf_path = create_quote_pdf(quote_row, get_quote_items(self.selected_quote_id))
        update_pdf_path(self.selected_quote_id, str(pdf_path))
        self.refresh_quotes()
        self.select_quote_by_id(self.selected_quote_id)
        self._show_info(f"PDF creato in: {pdf_path}")

    def generate_excel(self) -> None:
        if self.selected_quote_id is None:
            self._show_warning("Salva o seleziona un preventivo prima di esportare Excel.")
            return

        quote_row = get_quote(self.selected_quote_id)
        if quote_row is None:
            self._show_warning("Preventivo non trovato.")
            return

        excel_path = create_quote_excel(quote_row, get_quote_items(self.selected_quote_id))
        update_excel_path(self.selected_quote_id, str(excel_path))
        self.refresh_quotes()
        self.select_quote_by_id(self.selected_quote_id)
        self._show_info(f"File Excel creato in: {excel_path}")

    def export_registry_excel(self) -> None:
        excel_path = create_quotes_registry_excel(list_quotes(self.search_input.text()))
        self._show_info(f"Registro Excel creato in: {excel_path}")

    def configure_ai(self) -> None:
        current_model = get_configured_model()
        api_key, api_key_ok = QInputDialog.getText(
            self,
            "Configura OpenAI",
            "Inserisci la chiave API OpenAI:",
            QLineEdit.EchoMode.Password,
        )
        if not api_key_ok:
            return

        model_name, model_ok = QInputDialog.getText(
            self,
            "Modello AI",
            "Modello OpenAI da usare:",
            QLineEdit.EchoMode.Normal,
            current_model,
        )
        if not model_ok:
            return

        if api_key.strip():
            set_setting(API_KEY_SETTING, api_key.strip())
        if model_name.strip():
            set_setting(MODEL_SETTING, model_name.strip())
        self._refresh_ai_status_label()
        self._show_info("Configurazione AI salvata.")

    def remove_ai_key(self) -> None:
        remove_setting(API_KEY_SETTING)
        self._refresh_ai_status_label()
        self._show_info("Chiave API rimossa.")

    def generate_ai_content(self, *, mode: str) -> None:
        if not has_api_key():
            self._show_warning("Configura prima la chiave API OpenAI.")
            return

        context = self._build_ai_context()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            generated = generate_quote_texts(context)
        except AIServiceError as exc:
            self._show_warning(str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()

        if mode in ("opening", "both") and generated["opening_text"]:
            self.opening_text_input.setPlainText(generated["opening_text"])
        if mode in ("items", "both") and generated["included_items_text"]:
            self.included_items_input.setPlainText(generated["included_items_text"])
        self._show_info("Contenuto AI generato correttamente.")

    def _build_ai_context(self) -> dict[str, str]:
        items_summary = []
        for row_index in range(self.items_table.rowCount()):
            description_item = self.items_table.item(row_index, 0)
            quantity_item = self.items_table.item(row_index, 1)
            unit_price_item = self.items_table.item(row_index, 2)
            description = description_item.text().strip() if description_item else ""
            quantity = quantity_item.text().strip() if quantity_item else ""
            unit_price = unit_price_item.text().strip() if unit_price_item else ""
            if description:
                items_summary.append(f"{description} | qta {quantity} | prezzo {unit_price}")

        return {
            "client_name": self.client_selector.currentText().strip(),
            "client_contact_person": self.client_contact_input.text().strip(),
            "title": self.title_input.text().strip(),
            "work_site": self.work_site_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "included_items_text": self.included_items_input.toPlainText().strip(),
            "items_summary": "\n".join(items_summary),
        }

    def add_standard_included_items(self) -> None:
        existing_lines = {
            line.strip() for line in self.included_items_input.toPlainText().splitlines() if line.strip()
        }
        missing_lines = [line for line in STANDARD_INCLUDED_LINES if line not in existing_lines]
        if not missing_lines:
            self._show_info("Le voci standard sono gia presenti.")
            return

        current_lines = [line.strip() for line in self.included_items_input.toPlainText().splitlines() if line.strip()]
        current_lines.extend(missing_lines)
        self.included_items_input.setPlainText("\n".join(current_lines))

    def _refresh_ai_status_label(self) -> None:
        status = "configurata" if has_api_key() else "non configurata"
        model = get_configured_model()
        self.ai_status_label.setText(f"OpenAI: {status} | Modello: {model}")

    def _parse_float(self, value: str) -> float:
        normalized = value.strip().replace("EUR", "").replace(",", ".")
        try:
            return float(normalized or 0)
        except ValueError:
            return 0.0

    def _format_number(self, value: float) -> str:
        return f"{value:.2f}"

    def _format_currency(self, value: float) -> str:
        return f"EUR {value:.2f}"

    def _default_offer_date(self) -> str:
        return datetime.now().strftime("%d/%m/%Y")

    def _default_opening_text(self) -> str:
        return (
            "Facciamo seguito alla Vostra cortese richiesta e, con la presente, "
            "abbiamo il piacere di sottoporVi la nostra migliore offerta per lo "
            "svolgimento delle attivita presso il Vostro stabilimento."
        )

    def _default_included_items_text(self) -> str:
        return "\n".join(STANDARD_INCLUDED_LINES)

    def _default_closing_text(self) -> str:
        return "Cordiali saluti"

    def _default_signature_name(self) -> str:
        return "Pasquale Di Giovanni"

    def _show_warning(self, message: str) -> None:
        QMessageBox.warning(self, "Attenzione", message)

    def _show_info(self, message: str) -> None:
        QMessageBox.information(self, "Informazione", message)


def run() -> None:
    initialize_database()
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    app.exec()
