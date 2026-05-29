from __future__ import annotations

from io import BytesIO
import json
import mimetypes
from pathlib import Path
import re

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import load_workbook
from pydantic import BaseModel

from .reporting import generate_batch_report
from .runtime_paths import STATIC_DIR, TEMPLATES_DIR
from .store import (
    REPORTS_DIR,
    active_pallets,
    current_batch,
    delete_batch,
    finish_batch,
    get_item_by_pallet,
    import_items,
    init_db,
    list_batches,
    list_items,
    list_items_for_batch,
    mark_waiting_fiche,
    reset_pallet,
    register_incoming,
    register_outgoing,
    summary,
    update_pallet,
    wipe_all_data,
)


app = FastAPI(title="App riconfezionamento")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
init_db()


class IncomingScan(BaseModel):
    code: str
    operator_name: str


class OutgoingScan(BaseModel):
    pallet_code: str
    outgoing_code: str
    outgoing_zun: int
    outgoing_product_code: str
    operator_name: str
    allow_product_code_change: bool = False


class WaitingFicheAction(BaseModel):
    pallet_code: str
    operator_name: str


class CompletedPalletEdit(BaseModel):
    pallet_code: str
    incoming_code: str
    outgoing_code: str
    outgoing_zun: int
    product_code: str = ""
    operator_name: str
    batch_id: int | None = None


class PalletResetRequest(BaseModel):
    batch_id: int | None = None


class AdminWipeRequest(BaseModel):
    password: str


ADMIN_WIPE_PASSWORD = "Unilever_1992"


@app.on_event("startup")
def startup() -> None:
    init_db()


def _normalize_headers(values: tuple[object, ...] | list[object]) -> list[str]:
    return [str(value).strip() if value is not None else "" for value in values]


def _score_header_row(headers: list[str]) -> int:
    normalized = [header.lower() for header in headers if header]
    if not normalized:
        return 0

    score = len(normalized)
    score += sum(
        3
        for header in normalized
        if any(term in header for term in ["fiche", "prodotto", "codice", "motivo", "riconfezionamento", "q.ta", "zun"])
    )
    return score


def _resolve_sheet_and_header(
    workbook,
    sheet_name: str | None,
    header_row: int,
):
    if sheet_name and sheet_name not in workbook.sheetnames:
        raise HTTPException(status_code=400, detail="Foglio Excel non trovato.")

    worksheet = workbook[sheet_name] if sheet_name else workbook[workbook.sheetnames[0]]
    rows = list(worksheet.iter_rows(values_only=True))
    header_index = header_row - 1

    if header_index < 0:
        raise HTTPException(status_code=400, detail="Riga intestazioni non valida.")

    if header_index < len(rows):
        headers = _normalize_headers(rows[header_index])
        if any(headers):
            return worksheet, rows, header_index, headers

    if sheet_name:
        raise HTTPException(status_code=400, detail="Intestazioni non trovate nella riga selezionata.")

    best_match: tuple[int, object, list[tuple[object, ...]], int, list[str]] | None = None
    for candidate_sheet in workbook.worksheets:
        candidate_rows = list(candidate_sheet.iter_rows(values_only=True))
        for candidate_index, candidate_row in enumerate(candidate_rows[:25]):
            candidate_headers = _normalize_headers(candidate_row)
            score = _score_header_row(candidate_headers)
            if score <= 0:
                continue
            if best_match is None or score > best_match[0]:
                best_match = (score, candidate_sheet, candidate_rows, candidate_index, candidate_headers)

    if best_match is None:
        raise HTTPException(status_code=400, detail="Intestazioni non trovate nella riga selezionata.")

    _, worksheet, rows, header_index, headers = best_match
    return worksheet, rows, header_index, headers


def read_excel(file_bytes: bytes, header_row: int, sheet_name: str | None) -> tuple[str, int, list[str], list[dict[str, str]]]:
    workbook = load_workbook(BytesIO(file_bytes), data_only=True)
    worksheet, rows, header_index, headers = _resolve_sheet_and_header(workbook, sheet_name, header_row)

    data_rows: list[dict[str, str]] = []
    for row_offset, values in enumerate(rows[header_index + 1 :], start=1):
        record = {
            headers[index]: "" if value is None else str(value).strip()
            for index, value in enumerate(values)
            if index < len(headers) and headers[index]
        }
        if any(record.values()):
            record["__row_number"] = str(header_index + 1 + row_offset)
            data_rows.append(record)

    return worksheet.title, header_index + 1, headers, data_rows


def parse_zun(value: str) -> int:
    text = value.strip()
    if not text:
        return 0
    try:
        return int(float(text.replace(",", ".")))
    except ValueError:
        return 0


def resolve_reason_column(headers: list[str], requested_column: str) -> str:
    requested = requested_column.strip()
    normalized = {header: header.lower() for header in headers if header}
    preferred = [
        header
        for header, lower in normalized.items()
        if lower.startswith("motivo") or "motivo " in lower or "motivo_" in lower
    ]
    if not preferred:
        preferred = [
            header
            for header, lower in normalized.items()
            if "riconfezionamento" in lower and "costo" not in lower
        ]

    if preferred:
        if requested in preferred:
            return requested
        if not requested or "nota" in requested.lower() or "costo" in requested.lower():
            return preferred[0]

    return requested


def parse_row_actions(raw_actions: str) -> dict[int, dict[str, object]]:
    if not raw_actions.strip():
        return {}

    try:
        payload = json.loads(raw_actions)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Formato correzioni righe non valido.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Formato correzioni righe non valido.")

    normalized: dict[int, dict[str, object]] = {}
    for raw_key, raw_value in payload.items():
        try:
            row_number = int(str(raw_key).strip())
        except ValueError:
            continue
        if not isinstance(raw_value, dict):
            continue

        normalized[row_number] = {
            "reason": str(raw_value.get("reason", "")).strip(),
            "discard": bool(raw_value.get("discard", False)),
        }

    return normalized


def validate_import_columns(
    headers: list[str],
    incoming_column: str,
    pallet_column: str,
    outgoing_column: str,
    product_column: str,
    product_code_column: str,
    reason_column: str,
    zun_column: str,
) -> str:
    if not reason_column.strip():
        raise HTTPException(status_code=400, detail="Seleziona la colonna del motivo riconfezionamento.")
    if not product_code_column.strip():
        raise HTTPException(status_code=400, detail="Seleziona la colonna del codice prodotto.")

    resolved_reason_column = resolve_reason_column(headers, reason_column)
    missing_columns = [
        column
        for column in [incoming_column, pallet_column, outgoing_column, product_column, product_code_column, resolved_reason_column, zun_column]
        if column and column not in headers
    ]
    if missing_columns:
        raise HTTPException(status_code=400, detail=f"Colonne non trovate: {', '.join(missing_columns)}")

    return resolved_reason_column


def build_import_rows(
    rows: list[dict[str, str]],
    pallet_column: str,
    incoming_column: str,
    outgoing_column: str,
    product_column: str,
    product_code_column: str,
    reason_column: str,
    zun_column: str,
    row_actions: dict[int, dict[str, object]] | None = None,
    strict_empty: bool = True,
) -> tuple[list[dict[str, str | int]], list[dict[str, str]]]:
    imported_rows: list[dict[str, str | int]] = []
    last_product_name = ""
    last_product_code = ""
    last_repackaging_reason = ""
    missing_reason_rows: list[dict[str, str]] = []
    missing_product_code_rows: list[dict[str, str]] = []
    actions = row_actions or {}
    for row in rows:
        try:
            row_number = int(row.get("__row_number", "0") or 0)
        except ValueError:
            row_number = 0
        row_action = actions.get(row_number, {})
        selected_pallet_value = row.get(pallet_column, "").strip() if pallet_column else ""
        incoming_fiche = row.get(incoming_column, "").strip()
        outgoing_fiche = row.get(outgoing_column, "").strip() if outgoing_column else ""
        raw_product_name = row.get(product_column, "").strip() if product_column else ""
        raw_product_code = row.get(product_code_column, "").strip() if product_code_column else ""
        raw_repackaging_reason = str(row_action.get("reason", "")).strip() or (row.get(reason_column, "").strip() if reason_column else "")
        product_name = raw_product_name or last_product_name
        product_code = raw_product_code or last_product_code
        if raw_repackaging_reason:
            repackaging_reason = raw_repackaging_reason
        elif product_name and product_name == last_product_name:
            repackaging_reason = last_repackaging_reason
        else:
            repackaging_reason = ""
        zun_quantity = parse_zun(row.get(zun_column, "").strip()) if zun_column else 0
        if not incoming_fiche or re.search(r"\d", incoming_fiche) is None:
            continue
        # The operator flow needs a unique row key. The incoming fiche is the only
        # stable per-row identifier, while product codes can repeat across many rows.
        pallet_code = incoming_fiche
        if not pallet_code:
            continue
        if bool(row_action.get("discard", False)):
            continue
        if not repackaging_reason:
            missing_reason_rows.append(
                {
                    "row_number": str(row_number),
                    "fiche": incoming_fiche or pallet_code,
                    "pallet": selected_pallet_value or pallet_code,
                    "product_name": product_name or "prodotto non indicato",
                    "zun_quantity": str(zun_quantity),
                    "reason": "",
                }
            )
            continue
        if not product_code:
            missing_product_code_rows.append(
                {
                    "row_number": str(row_number),
                    "fiche": incoming_fiche or pallet_code,
                    "pallet": selected_pallet_value or pallet_code,
                    "product_name": product_name or "prodotto non indicato",
                    "zun_quantity": str(zun_quantity),
                    "reason": repackaging_reason or "-",
                }
            )
            continue

        if product_name:
            last_product_name = product_name
        if product_code:
            last_product_code = product_code
        if repackaging_reason:
            last_repackaging_reason = repackaging_reason

        imported_rows.append(
            {
                "pallet_code": pallet_code,
                "incoming_fiche": incoming_fiche,
                "outgoing_fiche": outgoing_fiche,
                "product_name": product_name,
                "product_code": product_code,
                "repackaging_reason": repackaging_reason,
                "zun_quantity": zun_quantity,
                "manual_reason_override": 1 if str(row_action.get("reason", "")).strip() else 0,
            }
        )

    if not imported_rows and strict_empty:
        if missing_product_code_rows:
            preview = ", ".join(row["fiche"] for row in missing_product_code_rows[:4])
            product_preview = missing_product_code_rows[0]["product_name"]
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        f"Codice prodotto mancante per {len(missing_product_code_rows)} righe del lotto. "
                        f"Prodotto coinvolto: {product_preview}. Fiches: {preview}. Correggi il file Excel e reimporta."
                    ),
                    "skipped_rows": missing_product_code_rows,
                },
            )
        if missing_reason_rows:
            preview = ", ".join(row["fiche"] for row in missing_reason_rows[:4])
            product_preview = missing_reason_rows[0]["product_name"]
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        f"Motivo riconfezionamento mancante per {len(missing_reason_rows)} righe del lotto. "
                        f"Prodotto coinvolto: {product_preview}. Fiches: {preview}."
                    ),
                    "skipped_rows": missing_reason_rows,
                },
            )
        raise HTTPException(status_code=400, detail="Nessun pallet valido trovato nel file Excel.")
    if missing_product_code_rows:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    f"Ci sono {len(missing_product_code_rows)} righe senza codice prodotto. "
                    "Correggi il file Excel e reimporta il lotto."
                ),
                "skipped_rows": missing_product_code_rows,
            },
        )
    return imported_rows, missing_reason_rows


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    base_path = str(request.scope.get("root_path") or "").rstrip("/")
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html.replace("__APP_BASE_PATH__", base_path))


@app.post("/api/preview")
async def preview_excel(
    file: UploadFile = File(...),
    header_row: int = Form(1),
    sheet_name: str = Form(""),
) -> dict[str, object]:
    content = await file.read()
    resolved_sheet_name, resolved_header_row, headers, rows = read_excel(content, header_row, sheet_name or None)
    return {
        "filename": file.filename,
        "sheet_names": load_workbook(BytesIO(content), read_only=True).sheetnames,
        "resolved_sheet_name": resolved_sheet_name,
        "resolved_header_row": resolved_header_row,
        "headers": headers,
        "preview": rows[:5],
        "row_count": len(rows),
    }


@app.post("/api/import/check")
async def check_import_excel(
    file: UploadFile = File(...),
    pallet_column: str = Form(""),
    incoming_column: str = Form(...),
    outgoing_column: str = Form(""),
    product_column: str = Form(""),
    product_code_column: str = Form(""),
    reason_column: str = Form(...),
    zun_column: str = Form(""),
    header_row: int = Form(1),
    sheet_name: str = Form(""),
) -> dict[str, object]:
    content = await file.read()
    _, _, headers, rows = read_excel(content, header_row, sheet_name or None)
    reason_column = validate_import_columns(
        headers,
        incoming_column,
        pallet_column,
        outgoing_column,
        product_column,
        product_code_column,
        reason_column,
        zun_column,
    )

    imported_rows, skipped_rows = build_import_rows(
        rows,
        pallet_column,
        incoming_column,
        outgoing_column,
        product_column,
        product_code_column,
        reason_column,
        zun_column,
        strict_empty=False,
    )
    if not imported_rows and not skipped_rows:
        raise HTTPException(status_code=400, detail="Nessun pallet valido trovato nel file Excel.")

    if skipped_rows:
        return {
            "message": f"Controllo completato: {len(skipped_rows)} righe da correggere o scartare prima dell'import.",
            "issues": skipped_rows,
            "valid_rows": len(imported_rows),
        }

    return {
        "message": f"Controllo completato: {len(imported_rows)} righe pronte per l'import.",
        "issues": [],
        "valid_rows": len(imported_rows),
    }


@app.post("/api/import")
async def import_excel(
    file: UploadFile = File(...),
    pallet_column: str = Form(""),
    incoming_column: str = Form(...),
    outgoing_column: str = Form(""),
    product_column: str = Form(""),
    product_code_column: str = Form(""),
    reason_column: str = Form(...),
    zun_column: str = Form(""),
    header_row: int = Form(1),
    sheet_name: str = Form(""),
    row_actions: str = Form(""),
) -> dict[str, object]:
    content = await file.read()
    _, _, headers, rows = read_excel(content, header_row, sheet_name or None)

    reason_column = validate_import_columns(
        headers,
        incoming_column,
        pallet_column,
        outgoing_column,
        product_column,
        product_code_column,
        reason_column,
        zun_column,
    )
    parsed_row_actions = parse_row_actions(row_actions)

    imported_rows, skipped_rows = build_import_rows(
        rows,
        pallet_column,
        incoming_column,
        outgoing_column,
        product_column,
        product_code_column,
        reason_column,
        zun_column,
        row_actions=parsed_row_actions,
    )
    if skipped_rows:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Ci sono ancora {len(skipped_rows)} righe da correggere o scartare prima dell'import.",
                "skipped_rows": skipped_rows,
            },
        )

    result = import_items(file.filename or "lotto.xlsx", imported_rows)
    discarded_count = sum(1 for action in parsed_row_actions.values() if bool(action.get("discard", False)))
    message = f"Lotto importato: {result['total_items']} pedane registrate."
    if discarded_count:
        message += f" {discarded_count} righe scartate su richiesta."
    return {
        "message": message,
        "summary": summary(result["batch_id"]),
        "skipped_rows": [],
        "partial_import": False,
    }


@app.delete("/api/batches/current")
def remove_current_batch() -> dict[str, object]:
    batch = current_batch()
    if batch is None:
        raise HTTPException(status_code=404, detail="Nessun lotto da cancellare.")

    deleted = delete_batch(int(batch["id"]))
    if deleted is None:
        raise HTTPException(status_code=404, detail="Nessun lotto da cancellare.")

    return {
        "message": f"Lotto eliminato: {deleted['filename']}",
        "summary": summary(),
        "items": list_items(),
        "active_pallets": active_pallets(),
    }


@app.post("/api/admin/wipe-all")
def admin_wipe_all(payload: AdminWipeRequest) -> dict[str, object]:
    if payload.password != ADMIN_WIPE_PASSWORD:
        raise HTTPException(status_code=403, detail="Password amministratore non valida.")

    deleted = wipe_all_data()
    return {
        "message": (
            "Tutti i lotti importati e i backup disponibili sono stati cancellati. "
            f"Report eliminati: {deleted['reports_deleted']}. Backup eliminati: {deleted['backups_deleted']}."
        ),
        "summary": summary(),
        "items": list_items(),
        "active_pallets": active_pallets(),
        "batches": list_batches(),
    }


@app.get("/api/dashboard")
def dashboard(batch_id: int | None = None) -> dict[str, object]:
    active_batch = current_batch()
    selected_batch_id = batch_id if batch_id is not None else (int(active_batch["id"]) if active_batch else None)
    return {
        "current_batch": active_batch,
        "selected_batch_id": selected_batch_id,
        "summary": summary(selected_batch_id),
        "items": list_items(batch_id=selected_batch_id),
        "active_pallets": active_pallets(batch_id=selected_batch_id),
        "batches": list_batches(),
        "can_operate": bool(
            active_batch
            and selected_batch_id == int(active_batch["id"])
            and active_batch.get("completed_at") is None
        ),
    }


@app.get("/api/items/{pallet_code}")
def item_detail(pallet_code: str, batch_id: int | None = None) -> dict[str, object]:
    item = get_item_by_pallet(pallet_code.strip(), batch_id=batch_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Pallet non presente.")
    return {"item": item}


@app.post("/api/scan/incoming")
def scan_incoming(payload: IncomingScan) -> dict[str, object]:
    success, message, item = register_incoming(payload.code.strip(), payload.operator_name.strip())
    if not success:
        raise HTTPException(status_code=400, detail={"message": message, "item": item})
    return {"message": message, "item": item, "summary": summary(), "active_pallets": active_pallets()}


@app.post("/api/scan/waiting-fiche")
def set_waiting_fiche(payload: WaitingFicheAction) -> dict[str, object]:
    success, message, item = mark_waiting_fiche(payload.pallet_code.strip(), payload.operator_name.strip())
    if not success:
        raise HTTPException(status_code=400, detail={"message": message, "item": item})
    return {"message": message, "item": item, "summary": summary(), "active_pallets": active_pallets()}


@app.post("/api/scan/outgoing")
def scan_outgoing(payload: OutgoingScan) -> dict[str, object]:
    success, message, item, error_code = register_outgoing(
        payload.pallet_code.strip(),
        payload.outgoing_code.strip(),
        payload.outgoing_zun,
        payload.outgoing_product_code.strip(),
        payload.operator_name.strip(),
        allow_product_code_change=payload.allow_product_code_change,
    )
    if not success:
        raise HTTPException(status_code=400, detail={"message": message, "item": item, "error_code": error_code})
    return {"message": message, "item": item, "summary": summary(), "active_pallets": active_pallets()}


@app.put("/api/items/{pallet_code}/completed")
def edit_completed_pallet(pallet_code: str, payload: CompletedPalletEdit) -> dict[str, object]:
    success, message, item = update_pallet(
        pallet_code.strip(),
        payload.pallet_code.strip(),
        payload.incoming_code.strip(),
        payload.outgoing_code.strip(),
        payload.outgoing_zun,
        payload.product_code.strip(),
        payload.operator_name.strip(),
        batch_id=payload.batch_id,
    )
    if not success:
        raise HTTPException(status_code=400, detail={"message": message, "item": item})
    return {"message": message, "item": item, "summary": summary(payload.batch_id), "active_pallets": active_pallets(payload.batch_id)}


@app.post("/api/items/{pallet_code}/reset")
def reset_item(pallet_code: str, payload: PalletResetRequest) -> dict[str, object]:
    success, message, item = reset_pallet(pallet_code.strip(), batch_id=payload.batch_id)
    if not success:
        raise HTTPException(status_code=400, detail={"message": message, "item": item})
    return {"message": message, "item": item, "summary": summary(payload.batch_id), "active_pallets": active_pallets(payload.batch_id)}


@app.post("/api/batches/current/finish")
def close_current_batch() -> dict[str, object]:
    batch = current_batch()
    if batch is None:
        raise HTTPException(status_code=400, detail="Nessun lotto disponibile.")

    batch_id = int(batch["id"])
    batch_summary = summary(batch_id)
    batch_items = list_items_for_batch(batch_id)
    report_path = generate_batch_report(REPORTS_DIR, batch, batch_items, batch_summary)
    finish_batch(str(report_path), batch_id=batch_id)
    updated_summary = summary(batch_id)
    return {
        "message": "Report Excel lotto generato con successo.",
        "summary": updated_summary,
        "report_url": f"/api/reports/{report_path.name}",
    }


@app.get("/api/reports/{report_name}")
def download_report(report_name: str) -> FileResponse:
    report_path = (REPORTS_DIR / report_name).resolve()
    if not report_path.exists() or report_path.parent != REPORTS_DIR.resolve():
        raise HTTPException(status_code=404, detail="Report non trovato.")
    media_type, _ = mimetypes.guess_type(report_path.name)
    return FileResponse(
        path=report_path,
        media_type=media_type or "application/octet-stream",
        filename=report_path.name,
    )