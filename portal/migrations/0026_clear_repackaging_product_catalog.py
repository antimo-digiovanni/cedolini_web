from pathlib import Path
import os
import sqlite3

from django.db import migrations
from openpyxl import Workbook


def clear_repackaging_product_catalog(apps, schema_editor):
    base_dir = Path(__file__).resolve().parents[2]
    data_dir = Path(os.getenv("APP_RICONFEZIONAMENTO_DATA_DIR", str(base_dir / "data"))).expanduser()
    catalog_path = Path(
        os.getenv(
            "APP_RICONFEZIONAMENTO_PRODUCTS_XLSX",
            str(data_dir / "Prodotti.xlsx"),
        )
    ).expanduser()
    db_path = data_dir / "repackaging.db"

    data_dir.mkdir(parents=True, exist_ok=True)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    try:
        worksheet = workbook.active
        worksheet.title = "Prodotti"
        worksheet.append(["Codice prodotto", "Prodotto"])
        workbook.save(catalog_path)
    finally:
        workbook.close()

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS product_catalog (
                product_code TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                normalized_product_name TEXT NOT NULL,
                synced_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_product_catalog_name ON product_catalog(normalized_product_name)"
        )
        connection.execute("DELETE FROM product_catalog")
        connection.commit()


def noop(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0025_remove_smart_agenda_models"),
    ]

    operations = [
        migrations.RunPython(clear_repackaging_product_catalog, noop),
    ]