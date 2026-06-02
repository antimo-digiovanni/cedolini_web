from __future__ import annotations

from pathlib import Path
import re
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from .runtime_paths import DATA_DIR, DB_PATH, REPORTS_DIR


ROME_TZ = ZoneInfo("Europe/Rome")


def now_iso() -> str:
    return datetime.now(ROME_TZ).isoformat(timespec="seconds")


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_product_name(value: object) -> str:
    normalized = normalize_text(value).casefold()
    return re.sub(r"\s+", " ", normalized)


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                total_items INTEGER NOT NULL,
                completed_at TEXT,
                report_path TEXT
            );

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                pallet_code TEXT NOT NULL,
                original_pallet_code TEXT NOT NULL DEFAULT '',
                incoming_fiche TEXT NOT NULL,
                original_incoming_fiche TEXT NOT NULL DEFAULT '',
                outgoing_fiche TEXT NOT NULL,
                original_outgoing_fiche TEXT NOT NULL DEFAULT '',
                product_name TEXT NOT NULL DEFAULT '',
                product_code TEXT NOT NULL DEFAULT '',
                original_product_code TEXT NOT NULL DEFAULT '',
                production_lot TEXT NOT NULL DEFAULT '',
                original_production_lot TEXT NOT NULL DEFAULT '',
                product_code_changed INTEGER NOT NULL DEFAULT 0,
                product_code_change_operator TEXT NOT NULL DEFAULT '',
                repackaging_reason TEXT NOT NULL DEFAULT '',
                manual_reason_override INTEGER NOT NULL DEFAULT 0,
                zun_quantity INTEGER NOT NULL DEFAULT 0,
                original_zun_quantity INTEGER NOT NULL DEFAULT 0,
                incoming_operator TEXT NOT NULL DEFAULT '',
                waiting_operator TEXT NOT NULL DEFAULT '',
                outgoing_operator TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'registered',
                scanned_incoming_at TEXT,
                scanned_outgoing_at TEXT,
                FOREIGN KEY (batch_id) REFERENCES import_batches(id)
            );

            CREATE INDEX IF NOT EXISTS idx_items_batch_id ON items(batch_id);
            CREATE INDEX IF NOT EXISTS idx_items_pallet ON items(pallet_code);
            CREATE INDEX IF NOT EXISTS idx_items_incoming ON items(incoming_fiche);
            CREATE INDEX IF NOT EXISTS idx_items_state ON items(state);

            CREATE TABLE IF NOT EXISTS product_catalog (
                product_code TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                normalized_product_name TEXT NOT NULL,
                synced_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_product_catalog_name ON product_catalog(normalized_product_name);
            """
        )

        batch_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(import_batches)").fetchall()
        }
        if "completed_at" not in batch_columns:
            connection.execute("ALTER TABLE import_batches ADD COLUMN completed_at TEXT")
        if "report_path" not in batch_columns:
            connection.execute("ALTER TABLE import_batches ADD COLUMN report_path TEXT")

        item_columns = {row["name"] for row in connection.execute("PRAGMA table_info(items)").fetchall()}
        if "original_pallet_code" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN original_pallet_code TEXT NOT NULL DEFAULT ''")
        if "original_incoming_fiche" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN original_incoming_fiche TEXT NOT NULL DEFAULT ''")
        if "original_outgoing_fiche" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN original_outgoing_fiche TEXT NOT NULL DEFAULT ''")
        if "product_name" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN product_name TEXT NOT NULL DEFAULT ''")
        if "product_code" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN product_code TEXT NOT NULL DEFAULT ''")
        if "original_product_code" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN original_product_code TEXT NOT NULL DEFAULT ''")
        if "production_lot" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN production_lot TEXT NOT NULL DEFAULT ''")
        if "original_production_lot" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN original_production_lot TEXT NOT NULL DEFAULT ''")
        if "product_code_changed" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN product_code_changed INTEGER NOT NULL DEFAULT 0")
        if "product_code_change_operator" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN product_code_change_operator TEXT NOT NULL DEFAULT ''")
        if "repackaging_reason" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN repackaging_reason TEXT NOT NULL DEFAULT ''")
        if "manual_reason_override" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN manual_reason_override INTEGER NOT NULL DEFAULT 0")
        if "zun_quantity" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN zun_quantity INTEGER NOT NULL DEFAULT 0")
        if "original_zun_quantity" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN original_zun_quantity INTEGER NOT NULL DEFAULT 0")
        if "incoming_operator" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN incoming_operator TEXT NOT NULL DEFAULT ''")
        if "waiting_operator" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN waiting_operator TEXT NOT NULL DEFAULT ''")
        if "outgoing_operator" not in item_columns:
            connection.execute("ALTER TABLE items ADD COLUMN outgoing_operator TEXT NOT NULL DEFAULT ''")
        connection.execute(
            "UPDATE items SET original_pallet_code = pallet_code WHERE original_pallet_code = ''"
        )
        connection.execute(
            "UPDATE items SET original_incoming_fiche = incoming_fiche WHERE original_incoming_fiche = ''"
        )
        connection.execute(
            "UPDATE items SET original_outgoing_fiche = outgoing_fiche WHERE original_outgoing_fiche = ''"
        )
        connection.execute(
            "UPDATE items SET original_product_code = product_code WHERE original_product_code = ''"
        )
        connection.execute(
            "UPDATE items SET original_production_lot = production_lot WHERE original_production_lot = ''"
        )
        connection.execute(
            "UPDATE items SET original_zun_quantity = zun_quantity WHERE original_zun_quantity = 0"
        )
        connection.commit()


def _resolve_batch(batch_id: int | None = None) -> sqlite3.Row | None:
    with get_connection() as connection:
        if batch_id is not None:
            return connection.execute(
                "SELECT * FROM import_batches WHERE id = ? LIMIT 1",
                (batch_id,),
            ).fetchone()

        batch = connection.execute(
            "SELECT * FROM import_batches WHERE completed_at IS NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if batch is not None:
            return batch
        return connection.execute("SELECT * FROM import_batches ORDER BY id DESC LIMIT 1").fetchone()


def current_batch() -> dict[str, str | int | None] | None:
    batch = _resolve_batch()
    return dict(batch) if batch else None


def list_batches(limit: int = 20) -> list[dict[str, str | int | None]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, filename, imported_at, total_items, completed_at, report_path
            FROM import_batches
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def import_items(filename: str, rows: list[dict[str, str | int]]) -> dict[str, int]:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO import_batches(filename, imported_at, total_items) VALUES (?, ?, ?)",
            (filename, now_iso(), len(rows)),
        )
        batch_id = cursor.lastrowid
        cursor.executemany(
            """
            INSERT INTO items(
                batch_id,
                pallet_code,
                original_pallet_code,
                incoming_fiche,
                original_incoming_fiche,
                outgoing_fiche,
                original_outgoing_fiche,
                product_name,
                product_code,
                original_product_code,
                production_lot,
                original_production_lot,
                repackaging_reason,
                manual_reason_override,
                zun_quantity,
                original_zun_quantity,
                state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'registered')
            """,
            [
                (
                    batch_id,
                    row["pallet_code"],
                    row["pallet_code"],
                    row["incoming_fiche"],
                    row["incoming_fiche"],
                    row["outgoing_fiche"],
                    row["outgoing_fiche"],
                    row["product_name"],
                    row.get("product_code", ""),
                    row.get("product_code", ""),
                    row.get("production_lot", ""),
                    row.get("production_lot", ""),
                    row["repackaging_reason"],
                    row.get("manual_reason_override", 0),
                    row["zun_quantity"],
                    row["zun_quantity"],
                )
                for row in rows
            ],
        )
        connection.commit()
    return {"batch_id": batch_id, "total_items": len(rows)}


def replace_product_catalog(rows: list[dict[str, str]]) -> int:
    synced_at = now_iso()
    catalog_rows = [
        (
            normalize_text(row.get("product_code", "")),
            normalize_text(row.get("product_name", "")),
            normalize_product_name(row.get("product_name", "")),
            synced_at,
        )
        for row in rows
        if normalize_text(row.get("product_code", "")) and normalize_text(row.get("product_name", ""))
    ]

    with get_connection() as connection:
        connection.execute("DELETE FROM product_catalog")
        if catalog_rows:
            connection.executemany(
                """
                INSERT INTO product_catalog(product_code, product_name, normalized_product_name, synced_at)
                VALUES (?, ?, ?, ?)
                """,
                catalog_rows,
            )
        connection.commit()
    return len(catalog_rows)


def get_product_catalog_by_codes(product_codes: list[str]) -> dict[str, dict[str, str]]:
    normalized_codes = sorted({normalize_text(code) for code in product_codes if normalize_text(code)})
    if not normalized_codes:
        return {}

    placeholders = ", ".join("?" for _ in normalized_codes)
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT product_code, product_name, normalized_product_name, synced_at
            FROM product_catalog
            WHERE product_code IN ({placeholders})
            """,
            normalized_codes,
        ).fetchall()
    return {
        str(row["product_code"]): {
            "product_code": str(row["product_code"]),
            "product_name": str(row["product_name"]),
            "normalized_product_name": str(row["normalized_product_name"]),
            "synced_at": str(row["synced_at"]),
        }
        for row in rows
    }


def get_product_catalog_by_names(product_names: list[str]) -> dict[str, list[dict[str, str]]]:
    normalized_names = sorted({normalize_product_name(name) for name in product_names if normalize_text(name)})
    if not normalized_names:
        return {}

    placeholders = ", ".join("?" for _ in normalized_names)
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT product_code, product_name, normalized_product_name, synced_at
            FROM product_catalog
            WHERE normalized_product_name IN ({placeholders})
            ORDER BY product_code
            """,
            normalized_names,
        ).fetchall()

    result: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = str(row["normalized_product_name"])
        result.setdefault(key, []).append(
            {
                "product_code": str(row["product_code"]),
                "product_name": str(row["product_name"]),
                "normalized_product_name": str(row["normalized_product_name"]),
                "synced_at": str(row["synced_at"]),
            }
        )
    return result


def list_product_catalog(limit: int = 500) -> list[dict[str, str]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT product_code, product_name, normalized_product_name, synced_at
            FROM product_catalog
            ORDER BY product_code
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [
        {
            "product_code": str(row["product_code"]),
            "product_name": str(row["product_name"]),
            "normalized_product_name": str(row["normalized_product_name"]),
            "synced_at": str(row["synced_at"]),
        }
        for row in rows
    ]


def delete_batch(batch_id: int | None = None) -> dict[str, str | int | None] | None:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return None

    report_path = normalize_text(batch["report_path"])
    with get_connection() as connection:
        connection.execute("DELETE FROM items WHERE batch_id = ?", (batch["id"],))
        connection.execute("DELETE FROM import_batches WHERE id = ?", (batch["id"],))
        connection.commit()

    if report_path:
        report_file = Path(report_path)
        if report_file.exists():
            report_file.unlink(missing_ok=True)

    return dict(batch)


def wipe_all_data() -> dict[str, int]:
    reports_deleted = 0
    backup_deleted = 0

    with get_connection() as connection:
        connection.execute("DELETE FROM items")
        connection.execute("DELETE FROM import_batches")
        connection.commit()

    if REPORTS_DIR.exists():
        for path in REPORTS_DIR.rglob("*"):
            if path.is_file():
                path.unlink(missing_ok=True)
                reports_deleted += 1

    for pattern in ("*.bak", "*.backup", "*.old"):
        for path in DATA_DIR.glob(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)
                backup_deleted += 1

    return {
        "reports_deleted": reports_deleted,
        "backups_deleted": backup_deleted,
    }


def summary(batch_id: int | None = None) -> dict[str, int | str | None]:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return {
            "batch_id": None,
            "registered": 0,
            "in_progress": 0,
            "waiting_fiche": 0,
            "completed": 0,
            "last_filename": None,
            "last_imported_at": None,
            "completed_at": None,
            "report_path": None,
            "total_items": 0,
        }

    with get_connection() as connection:
        counts = {
            row["state"]: row["count"]
            for row in connection.execute(
                "SELECT state, COUNT(*) AS count FROM items WHERE batch_id = ? GROUP BY state",
                (batch["id"],),
            ).fetchall()
        }
    return {
        "batch_id": batch["id"],
        "registered": counts.get("registered", 0),
        "in_progress": counts.get("in_progress", 0),
        "waiting_fiche": counts.get("waiting_fiche", 0),
        "completed": counts.get("completed", 0),
        "last_filename": batch["filename"],
        "last_imported_at": batch["imported_at"],
        "completed_at": batch["completed_at"],
        "report_path": batch["report_path"],
        "total_items": batch["total_items"],
    }


def list_items(limit: int = 250, batch_id: int | None = None) -> list[dict[str, str | int | None]]:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return []

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, batch_id, pallet_code, incoming_fiche, outgoing_fiche, product_name, product_code, production_lot,
                                         original_outgoing_fiche, repackaging_reason, manual_reason_override, zun_quantity,
                                     original_zun_quantity, product_code_changed, product_code_change_operator, incoming_operator, waiting_operator,
                   outgoing_operator, state, scanned_incoming_at, scanned_outgoing_at
            FROM items
            WHERE batch_id = ?
            ORDER BY
                CASE state
                    WHEN 'in_progress' THEN 0
                    WHEN 'waiting_fiche' THEN 1
                    WHEN 'registered' THEN 2
                    ELSE 3
                END,
                pallet_code ASC
            LIMIT ?
            """,
            (batch["id"], limit),
        ).fetchall()
    return [dict(row) for row in rows]


def list_items_for_batch(batch_id: int) -> list[dict[str, str | int | None]]:
    return list_items(limit=10000, batch_id=batch_id)


def active_pallets(batch_id: int | None = None) -> list[dict[str, str]]:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return []

    with get_connection() as connection:
        rows = connection.execute(
            """
                        SELECT incoming_fiche AS pallet_code, state, product_name, product_code
            FROM items
            WHERE batch_id = ?
              AND state IN ('in_progress', 'waiting_fiche')
                        ORDER BY CASE state WHEN 'in_progress' THEN 0 ELSE 1 END, incoming_fiche
            """,
            (batch["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


def get_item_by_pallet(pallet_code: str, batch_id: int | None = None) -> dict[str, str | int | None] | None:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return None

    with get_connection() as connection:
        row = connection.execute(
                        """
                        SELECT *
                        FROM items
                        WHERE batch_id = ?
                            AND (incoming_fiche = ? OR pallet_code = ?)
                        ORDER BY CASE WHEN incoming_fiche = ? THEN 0 ELSE 1 END
                        LIMIT 1
                        """,
                        (batch["id"], pallet_code, pallet_code, pallet_code),
        ).fetchone()
    return dict(row) if row else None


def _get_item_by_incoming_scan(scan_code: str, batch_id: int | None = None) -> sqlite3.Row | None:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return None

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM items
            WHERE batch_id = ?
              AND (pallet_code = ? OR incoming_fiche = ?)
            ORDER BY CASE WHEN pallet_code = ? THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (batch["id"], scan_code, scan_code, scan_code),
        ).fetchone()


def register_incoming(
    scan_code: str,
    operator_name: str,
    batch_id: int | None = None,
) -> tuple[bool, str, dict[str, str | int | None] | None]:
    item = _get_item_by_incoming_scan(scan_code, batch_id=batch_id)
    if item is None:
        return False, "Codice non presente nel lotto attivo.", None
    if item["state"] == "completed":
        return False, "Pallet gia' completato.", dict(item)
    if item["state"] == "in_progress":
        return True, "Pallet gia' in lavorazione.", dict(item)
    if item["state"] == "waiting_fiche":
        return True, "Pallet in attesa di fiches.", dict(item)

    with get_connection() as connection:
        connection.execute(
            "UPDATE items SET state = 'in_progress', scanned_incoming_at = ?, incoming_operator = ? WHERE id = ?",
            (now_iso(), operator_name, item["id"]),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM items WHERE id = ?", (item["id"],)).fetchone()
    return True, "OK entrata: pallet registrato in lavorazione.", dict(updated) if updated else None


def mark_waiting_fiche(
    pallet_code: str,
    operator_name: str,
    batch_id: int | None = None,
) -> tuple[bool, str, dict[str, str | int | None] | None]:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return False, "Nessun lotto attivo.", None

    with get_connection() as connection:
        item = connection.execute(
                        """
                        SELECT *
                        FROM items
                        WHERE batch_id = ?
                            AND (incoming_fiche = ? OR pallet_code = ?)
                        ORDER BY CASE WHEN incoming_fiche = ? THEN 0 ELSE 1 END
                        LIMIT 1
                        """,
                        (batch["id"], pallet_code, pallet_code, pallet_code),
        ).fetchone()
        if item is None:
            return False, "Pallet selezionato non presente.", None
        if item["state"] == "registered":
            return False, "Prima va registrata l'entrata del pallet.", dict(item)
        if item["state"] == "completed":
            return False, "Pallet gia' chiuso.", dict(item)
        if item["state"] == "waiting_fiche":
            return True, "Pallet gia' in attesa di fiches.", dict(item)

        connection.execute(
            "UPDATE items SET state = 'waiting_fiche', waiting_operator = ? WHERE id = ?",
            (operator_name, item["id"]),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM items WHERE id = ?", (item["id"],)).fetchone()
    return True, "Pallet messo in attesa di fiches.", dict(updated) if updated else None


def register_outgoing(
    pallet_code: str,
    outgoing_scan: str,
    outgoing_zun: int,
    outgoing_product_code: str,
    operator_name: str,
    allow_product_code_change: bool = False,
    batch_id: int | None = None,
) -> tuple[bool, str, dict[str, str | int | None] | None, str | None]:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return False, "Nessun lotto attivo.", None, None

    with get_connection() as connection:
        item = connection.execute(
                        """
                        SELECT *
                        FROM items
                        WHERE batch_id = ?
                            AND (incoming_fiche = ? OR pallet_code = ?)
                        ORDER BY CASE WHEN incoming_fiche = ? THEN 0 ELSE 1 END
                        LIMIT 1
                        """,
                        (batch["id"], pallet_code, pallet_code, pallet_code),
        ).fetchone()
        if item is None:
            return False, "Pallet selezionato non presente.", None, None
        if item["state"] == "registered":
            return False, "Prima va registrata l'entrata del pallet.", dict(item), None
        if item["state"] == "completed":
            return False, "Pallet gia' chiuso.", dict(item), None

        if outgoing_zun <= 0:
            return False, "Inserisci uno ZUN finale valido.", dict(item), None
        if int(outgoing_zun) > int(item["zun_quantity"]):
            return False, "Lo ZUN finale non puo' superare lo ZUN del pallet in ingresso.", dict(item), None

        outgoing_value = normalize_text(outgoing_scan)
        outgoing_product_value = normalize_text(outgoing_product_code)
        expected_outgoing = normalize_text(item["outgoing_fiche"])
        expected_product_code = normalize_text(item["product_code"])
        if expected_outgoing and outgoing_value != expected_outgoing:
            return False, "Fiche di uscita non corretta.", dict(item), None
        if outgoing_value and outgoing_value in {
            normalize_text(item["pallet_code"]),
            normalize_text(item["incoming_fiche"]),
            normalize_text(item["outgoing_fiche"]),
        }:
            return False, "La nuova fiche deve essere diversa dalla fiche di entrata e da qualsiasi riferimento gia' registrato per questa pedana.", dict(item), None
        if not outgoing_product_value:
            return False, "Inserisci il codice prodotto riportato sulla nuova fiche.", dict(item), "missing_product_code"
        if not expected_product_code:
            return False, (
                "Per questo pallet manca il codice prodotto importato dall'Excel. "
                "Correggi il lotto e reimporta prima di chiudere la rilavorazione."
            ), dict(item), "missing_expected_product_code"
        if expected_product_code and outgoing_product_value != expected_product_code and not allow_product_code_change:
            return False, (
                f"Il codice prodotto {outgoing_product_value} non coincide con il codice in entrata {expected_product_code}. "
                "Se la rilavorazione riguarda un cambio codice prodotto, conferma l'eccezione."
            ), dict(item), "product_code_mismatch"

        duplicate = connection.execute(
            """
            SELECT id
            FROM items
            WHERE id <> ?
              AND (? <> '')
              AND (pallet_code = ? OR incoming_fiche = ? OR outgoing_fiche = ?)
            LIMIT 1
            """,
            (item["id"], outgoing_value, outgoing_value, outgoing_value, outgoing_value),
        ).fetchone()
        if duplicate is not None:
            return False, "La nuova fiche risulta gia' presente nel lotto. Deve essere una fiche nuova generata dall'altro sistema.", dict(item), None

        connection.execute(
            """
            UPDATE items
            SET outgoing_fiche = ?,
                zun_quantity = ?,
                product_code = ?,
                product_code_changed = ?,
                product_code_change_operator = ?,
                state = 'completed',
                scanned_outgoing_at = ?,
                outgoing_operator = ?
            WHERE id = ?
            """,
            (
                outgoing_value,
                int(outgoing_zun),
                outgoing_product_value,
                1 if expected_product_code and outgoing_product_value != expected_product_code else 0,
                operator_name if expected_product_code and outgoing_product_value != expected_product_code else "",
                now_iso(),
                operator_name,
                item["id"],
            ),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM items WHERE id = ?", (item["id"],)).fetchone()
    if expected_outgoing:
        if expected_product_code and outgoing_product_value != expected_product_code:
            return True, "OK uscita: processo completato con cambio codice prodotto registrato.", dict(updated) if updated else None, None
        return True, "OK uscita: processo completato.", dict(updated) if updated else None, None
    if expected_product_code and outgoing_product_value != expected_product_code:
        return True, "OK uscita: nuova fiche registrata con cambio codice prodotto.", dict(updated) if updated else None, None
    return True, "OK uscita: nuova fiche registrata e processo completato.", dict(updated) if updated else None, None


def update_pallet(
    pallet_code: str,
    new_pallet_code: str,
    incoming_scan: str,
    outgoing_scan: str,
    outgoing_zun: int,
    product_code: str,
    operator_name: str,
    batch_id: int | None = None,
) -> tuple[bool, str, dict[str, str | int | None] | None]:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return False, "Nessun lotto disponibile.", None

    pallet_value = normalize_text(new_pallet_code)
    if not pallet_value:
        return False, "Inserisci il numero pallet da salvare.", None

    incoming_value = normalize_text(incoming_scan)
    if not incoming_value:
        return False, "Inserisci la fiche di entrata da salvare.", None

    outgoing_value = normalize_text(outgoing_scan)
    product_code_value = normalize_text(product_code)
    if outgoing_zun <= 0:
        return False, "Inserisci uno ZUN finale valido.", None

    with get_connection() as connection:
        item = connection.execute(
            "SELECT * FROM items WHERE batch_id = ? AND pallet_code = ? LIMIT 1",
            (batch["id"], pallet_code),
        ).fetchone()
        if item is None:
            return False, "Pallet selezionato non presente.", None

        duplicate = connection.execute(
            """
            SELECT id
            FROM items
            WHERE id <> ?
              AND (
                                ((? <> '') AND pallet_code = ?)
                                OR
                ((? <> '') AND (pallet_code = ? OR incoming_fiche = ? OR outgoing_fiche = ?))
                OR
                ((? <> '') AND (pallet_code = ? OR incoming_fiche = ? OR outgoing_fiche = ?))
              )
            LIMIT 1
            """,
            (
                item["id"],
                                pallet_value,
                                pallet_value,
                incoming_value,
                incoming_value,
                incoming_value,
                incoming_value,
                outgoing_value,
                outgoing_value,
                outgoing_value,
                outgoing_value,
            ),
        ).fetchone()
        if duplicate is not None:
            return False, "Il numero pallet o una delle fiches risulta gia' usata a sistema.", dict(item)

        operator_value = normalize_text(operator_name)
        scanned_outgoing_at = item["scanned_outgoing_at"] if item["state"] == "completed" and outgoing_value else None
        outgoing_operator = operator_value if item["state"] == "completed" and outgoing_value else item["outgoing_operator"]

        connection.execute(
            """
            UPDATE items
            SET pallet_code = ?,
                incoming_fiche = ?,
                outgoing_fiche = ?,
                product_code = ?,
                zun_quantity = ?,
                incoming_operator = CASE
                    WHEN ? = '' OR state = 'registered' THEN incoming_operator
                    ELSE ?
                END,
                outgoing_operator = CASE
                    WHEN ? = '' THEN outgoing_operator
                    ELSE ?
                END,
                scanned_outgoing_at = ?
            WHERE id = ?
            """,
            (
                pallet_value,
                incoming_value,
                outgoing_value,
                product_code_value,
                int(outgoing_zun),
                operator_value,
                operator_value,
                operator_value,
                outgoing_operator,
                scanned_outgoing_at,
                item["id"],
            ),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM items WHERE id = ?", (item["id"],)).fetchone()
    return True, "Pallet aggiornato correttamente.", dict(updated) if updated else None


def reset_pallet(pallet_code: str, batch_id: int | None = None) -> tuple[bool, str, dict[str, str | int | None] | None]:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return False, "Nessun lotto disponibile.", None

    with get_connection() as connection:
        item = connection.execute(
            "SELECT * FROM items WHERE batch_id = ? AND pallet_code = ? LIMIT 1",
            (batch["id"], pallet_code),
        ).fetchone()
        if item is None:
            return False, "Pallet selezionato non presente.", None

        connection.execute(
            """
            UPDATE items
            SET pallet_code = original_pallet_code,
                incoming_fiche = original_incoming_fiche,
                outgoing_fiche = original_outgoing_fiche,
                product_code = original_product_code,
                zun_quantity = original_zun_quantity,
                product_code_changed = 0,
                product_code_change_operator = '',
                incoming_operator = '',
                waiting_operator = '',
                outgoing_operator = '',
                state = 'registered',
                scanned_incoming_at = NULL,
                scanned_outgoing_at = NULL
            WHERE id = ?
            """,
            (item["id"],),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM items WHERE id = ?", (item["id"],)).fetchone()
    return True, "Pallet riportato allo stato iniziale del lotto.", dict(updated) if updated else None


def finish_batch(report_path: str, batch_id: int | None = None) -> dict[str, str | int | None] | None:
    batch = _resolve_batch(batch_id)
    if batch is None:
        return None

    with get_connection() as connection:
        connection.execute(
            "UPDATE import_batches SET completed_at = ?, report_path = ? WHERE id = ?",
            (now_iso(), report_path, batch["id"]),
        )
        connection.commit()
    updated = _resolve_batch(batch["id"])
    return dict(updated) if updated else None