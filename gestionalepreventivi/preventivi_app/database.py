import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from preventivi_app.models import ClientInput, QuoteInput, QuoteItemInput


BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "preventivi.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                progressive_number INTEGER NOT NULL UNIQUE,
                quote_code TEXT NOT NULL UNIQUE,
                client_name TEXT NOT NULL,
                client_contact_person TEXT NOT NULL DEFAULT '',
                client_email TEXT NOT NULL DEFAULT '',
                client_phone TEXT NOT NULL DEFAULT '',
                client_address TEXT NOT NULL DEFAULT '',
                offer_date TEXT NOT NULL DEFAULT '',
                recipient_attention TEXT NOT NULL DEFAULT '',
                work_site TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                opening_text TEXT NOT NULL DEFAULT '',
                included_items_text TEXT NOT NULL DEFAULT '',
                amount REAL NOT NULL,
                payment_reference TEXT NOT NULL DEFAULT '',
                payment_status TEXT NOT NULL,
                quote_status TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                closing_text TEXT NOT NULL DEFAULT '',
                signature_name TEXT NOT NULL DEFAULT '',
                include_discount_note INTEGER NOT NULL DEFAULT 0,
                pdf_path TEXT,
                excel_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                contact_person TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS quote_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id INTEGER NOT NULL,
                line_number INTEGER NOT NULL,
                description TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                total_amount REAL NOT NULL,
                FOREIGN KEY (quote_id) REFERENCES quotes (id) ON DELETE CASCADE
            )
            """
        )
        _ensure_quotes_columns(connection)
        connection.commit()


def _ensure_quotes_columns(connection: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(quotes)").fetchall()
    }
    columns_to_add = {
        "client_contact_person": "TEXT NOT NULL DEFAULT ''",
        "client_email": "TEXT NOT NULL DEFAULT ''",
        "client_phone": "TEXT NOT NULL DEFAULT ''",
        "client_address": "TEXT NOT NULL DEFAULT ''",
        "offer_date": "TEXT NOT NULL DEFAULT ''",
        "recipient_attention": "TEXT NOT NULL DEFAULT ''",
        "work_site": "TEXT NOT NULL DEFAULT ''",
        "opening_text": "TEXT NOT NULL DEFAULT ''",
        "included_items_text": "TEXT NOT NULL DEFAULT ''",
        "payment_reference": "TEXT NOT NULL DEFAULT ''",
        "closing_text": "TEXT NOT NULL DEFAULT ''",
        "signature_name": "TEXT NOT NULL DEFAULT ''",
        "include_discount_note": "INTEGER NOT NULL DEFAULT 0",
        "excel_path": "TEXT",
    }

    for column_name, column_sql in columns_to_add.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE quotes ADD COLUMN {column_name} {column_sql}"
            )


def get_next_progressive_number() -> int:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COALESCE(MAX(progressive_number), 0) + 1 AS next_number FROM quotes"
        ).fetchone()
    return int(row["next_number"])


def build_quote_code(progressive_number: int) -> str:
    return str(int(progressive_number))


def list_clients() -> List[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM clients ORDER BY name COLLATE NOCASE"
        ).fetchall()


def get_client_by_name(client_name: str) -> Optional[sqlite3.Row]:
    normalized_name = client_name.strip()
    if not normalized_name:
        return None

    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM clients WHERE name = ? COLLATE NOCASE",
            (normalized_name,),
        ).fetchone()


def upsert_client(client: ClientInput) -> int:
    existing_client = get_client_by_name(client.name)

    with get_connection() as connection:
        if existing_client is None:
            cursor = connection.execute(
                """
                INSERT INTO clients (name, contact_person, email, phone, address, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    client.name.strip(),
                    client.contact_person.strip(),
                    client.email.strip(),
                    client.phone.strip(),
                    client.address.strip(),
                    client.notes.strip(),
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

        connection.execute(
            """
            UPDATE clients
            SET name = ?,
                contact_person = ?,
                email = ?,
                phone = ?,
                address = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                client.name.strip(),
                client.contact_person.strip(),
                client.email.strip(),
                client.phone.strip(),
                client.address.strip(),
                client.notes.strip(),
                existing_client["id"],
            ),
        )
        connection.commit()
        return int(existing_client["id"])


def insert_quote(quote: QuoteInput) -> int:
    progressive_number = int(quote.progressive_number)
    quote_code = build_quote_code(progressive_number)
    amount = _calculate_total_amount(quote)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO quotes (
                progressive_number,
                quote_code,
                client_name,
                client_contact_person,
                client_email,
                client_phone,
                client_address,
                offer_date,
                recipient_attention,
                work_site,
                title,
                description,
                opening_text,
                included_items_text,
                amount,
                payment_reference,
                payment_status,
                quote_status,
                notes,
                closing_text,
                signature_name,
                include_discount_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                progressive_number,
                quote_code,
                quote.client_name,
                quote.client_contact_person,
                quote.client_email,
                quote.client_phone,
                quote.client_address,
                quote.offer_date,
                quote.recipient_attention,
                quote.work_site,
                quote.title,
                quote.description,
                quote.opening_text,
                quote.included_items_text,
                amount,
                quote.payment_reference,
                quote.payment_status,
                quote.quote_status,
                quote.notes,
                quote.closing_text,
                quote.signature_name,
                int(quote.include_discount_note),
            ),
        )
        quote_id = int(cursor.lastrowid)
        _replace_quote_items(connection, quote_id, quote.items)
        connection.commit()
        return quote_id


def update_quote(quote_id: int, quote: QuoteInput) -> None:
    amount = _calculate_total_amount(quote)
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE quotes
            SET progressive_number = ?,
                quote_code = ?,
                client_name = ?,
                client_contact_person = ?,
                client_email = ?,
                client_phone = ?,
                client_address = ?,
                offer_date = ?,
                recipient_attention = ?,
                work_site = ?,
                title = ?,
                description = ?,
                opening_text = ?,
                included_items_text = ?,
                amount = ?,
                payment_reference = ?,
                payment_status = ?,
                quote_status = ?,
                notes = ?,
                closing_text = ?,
                signature_name = ?,
                include_discount_note = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                int(quote.progressive_number),
                build_quote_code(int(quote.progressive_number)),
                quote.client_name,
                quote.client_contact_person,
                quote.client_email,
                quote.client_phone,
                quote.client_address,
                quote.offer_date,
                quote.recipient_attention,
                quote.work_site,
                quote.title,
                quote.description,
                quote.opening_text,
                quote.included_items_text,
                amount,
                quote.payment_reference,
                quote.payment_status,
                quote.quote_status,
                quote.notes,
                quote.closing_text,
                quote.signature_name,
                int(quote.include_discount_note),
                quote_id,
            ),
        )
        _replace_quote_items(connection, quote_id, quote.items)
        connection.commit()


def _replace_quote_items(
    connection: sqlite3.Connection,
    quote_id: int,
    items: List[QuoteItemInput],
) -> None:
    connection.execute("DELETE FROM quote_items WHERE quote_id = ?", (quote_id,))

    for line_number, item in enumerate(items, start=1):
        connection.execute(
            """
            INSERT INTO quote_items (
                quote_id,
                line_number,
                description,
                quantity,
                unit_price,
                total_amount
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                quote_id,
                line_number,
                item.description,
                item.quantity,
                item.unit_price,
                item.total_amount,
            ),
        )


def _calculate_total_amount(quote: QuoteInput) -> float:
    return round(float(quote.amount), 2)


def update_quote_status(
    quote_id: int,
    *,
    payment_status: Optional[str] = None,
    quote_status: Optional[str] = None,
    payment_reference: Optional[str] = None,
) -> None:
    assignments = []
    values = []

    if payment_status is not None:
        assignments.append("payment_status = ?")
        values.append(payment_status)
    if quote_status is not None:
        assignments.append("quote_status = ?")
        values.append(quote_status)
    if payment_reference is not None:
        assignments.append("payment_reference = ?")
        values.append(payment_reference)

    if not assignments:
        return

    assignments.append("updated_at = CURRENT_TIMESTAMP")
    values.append(quote_id)
    query = f"UPDATE quotes SET {', '.join(assignments)} WHERE id = ?"

    with get_connection() as connection:
        connection.execute(query, values)
        connection.commit()


def update_pdf_path(quote_id: int, pdf_path: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE quotes
            SET pdf_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (pdf_path, quote_id),
        )
        connection.commit()


def update_excel_path(quote_id: int, excel_path: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE quotes
            SET excel_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (excel_path, quote_id),
        )
        connection.commit()


def get_quote(quote_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM quotes WHERE id = ?",
            (quote_id,),
        ).fetchone()


def get_quote_items(quote_id: int) -> List[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM quote_items WHERE quote_id = ? ORDER BY line_number",
            (quote_id,),
        ).fetchall()


def list_quotes(search_text: str = "", payment_status: str = "") -> List[sqlite3.Row]:
    normalized_search = f"%{search_text.strip()}%"
    normalized_payment_status = payment_status.strip()
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM quotes
            WHERE (
                (? = '%%')
                OR client_name LIKE ?
                OR title LIKE ?
                OR quote_code LIKE ?
                OR client_email LIKE ?
                OR client_phone LIKE ?
            )
              AND (? = '' OR payment_status = ?)
            ORDER BY progressive_number DESC
            """,
            (
                normalized_search,
                normalized_search,
                normalized_search,
                normalized_search,
                normalized_search,
                normalized_search,
                normalized_payment_status,
                normalized_payment_status,
            ),
        ).fetchall()


def get_dashboard_counts() -> Dict[str, int]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                SUM(CASE WHEN payment_status = 'Pending' THEN 1 ELSE 0 END) AS pending_count,
                SUM(CASE WHEN payment_status = 'Pagato' THEN 1 ELSE 0 END) AS paid_count,
                SUM(CASE WHEN quote_status = 'Da confermare' THEN 1 ELSE 0 END) AS to_confirm_count,
                SUM(CASE WHEN quote_status = 'Confermato' THEN 1 ELSE 0 END) AS confirmed_count,
                SUM(CASE WHEN quote_status = 'Lavoro fatto' THEN 1 ELSE 0 END) AS work_done_count
            FROM quotes
            """
        ).fetchone()

    return {
        "pending": int(row["pending_count"] or 0),
        "paid": int(row["paid_count"] or 0),
        "to_confirm": int(row["to_confirm_count"] or 0),
        "confirmed": int(row["confirmed_count"] or 0),
        "work_done": int(row["work_done_count"] or 0),
    }
