from __future__ import annotations

import argparse
import logging
import os
import queue
import re
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pypdf import PdfReader, PdfWriter


logging.getLogger("pypdf").setLevel(logging.ERROR)

START_MARKER = "CERTIFICAZIONE DI CUI"
DEFAULT_INPUT = Path(r"C:\Users\antim\Downloads\CU2026 San Vincenzo con ricevuta.pdf")
DEFAULT_OUTPUT_DIR = Path(r"C:\Users\antim\Downloads\San Vincenzo CUD divisi")


@dataclass(frozen=True)
class EmployeeCudBlock:
    surname: str
    name: str
    fiscal_code: str
    start_page: int
    end_page: int
    output_filename: str

    @property
    def page_count(self) -> int:
        return self.end_page - self.start_page + 1


def normalize_text(value: str) -> str:
    return value.replace("�", "'").replace("’", "'")


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def clean_identity_value(value: str) -> str:
    value = normalize_text(value).upper().strip()
    value = re.sub(r"[^A-Z0-9' -]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def slug_for_filename(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.upper().replace("'", "_")
    value = re.sub(r"[^A-Z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_") or "DOCUMENTO"


def detect_document_label(input_pdf: Path) -> str:
    stem = input_pdf.stem.upper().replace("_", " ")
    match = re.search(r"\bCUD?\s*([12][0-9]{3})\b", stem)
    if match:
        return f"CU{match.group(1)}"
    return "CU"


def page_is_employee_start(page) -> bool:
    text = (page.extract_text() or "").upper()
    return (
        START_MARKER in text
        and "DATI RELATIVI AL" in text
        and "PERCETTORE" in text
    )


def extract_employee_identity(page) -> tuple[str, str, str]:
    layout_text = normalize_text(page.extract_text(extraction_mode="layout") or "")
    for raw_line in layout_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("PERCETTORE"):
            continue
        payload = re.sub(r"^PERCETTORE\s+", "", line)
        parts = [part.strip() for part in re.split(r"\s{2,}", payload) if part.strip()]
        if len(parts) >= 3 and re.fullmatch(r"[A-Z0-9]{16}", parts[0]):
            fiscal_code = clean_identity_value(parts[0])
            surname = clean_identity_value(parts[1])
            name = clean_identity_value(parts[2])
            if surname and name:
                return surname, name, fiscal_code

    compact = collapse_spaces(layout_text)
    match = re.search(
        r"PERCETTORE\s+([A-Z0-9]{16})\s+(.+?)\s+DELLE SOMME",
        compact,
    )
    if not match:
        raise ValueError("Impossibile leggere cognome, nome e codice fiscale dalla pagina iniziale")

    fiscal_code = clean_identity_value(match.group(1))
    name_bits = [clean_identity_value(bit) for bit in match.group(2).split(" ") if clean_identity_value(bit)]
    if len(name_bits) < 2:
        raise ValueError("Dati anagrafici incompleti nella pagina iniziale del CUD")
    surname = name_bits[0]
    name = " ".join(name_bits[1:])
    return surname, name, fiscal_code


def build_blocks(reader: PdfReader, document_label: str) -> tuple[int, list[EmployeeCudBlock]]:
    start_pages = [index for index, page in enumerate(reader.pages) if page_is_employee_start(page)]
    if not start_pages:
        raise ValueError("Nessuna certificazione dipendente trovata nel PDF")

    front_pages = start_pages[0]
    used_filenames: set[str] = set()
    blocks: list[EmployeeCudBlock] = []

    for position, start_page in enumerate(start_pages):
        end_page = start_pages[position + 1] - 1 if position + 1 < len(start_pages) else len(reader.pages) - 1
        surname, name, fiscal_code = extract_employee_identity(reader.pages[start_page])
        filename = build_unique_filename(document_label, surname, name, fiscal_code, used_filenames)
        blocks.append(
            EmployeeCudBlock(
                surname=surname,
                name=name,
                fiscal_code=fiscal_code,
                start_page=start_page,
                end_page=end_page,
                output_filename=filename,
            )
        )

    return front_pages, blocks


def build_unique_filename(
    document_label: str,
    surname: str,
    name: str,
    fiscal_code: str,
    used_filenames: set[str],
) -> str:
    base = f"{slug_for_filename(document_label)}_{slug_for_filename(surname)}_{slug_for_filename(name)}"
    candidate = f"{base}.pdf"
    if candidate not in used_filenames:
        used_filenames.add(candidate)
        return candidate

    candidate = f"{base}_{fiscal_code}.pdf"
    if candidate not in used_filenames:
        used_filenames.add(candidate)
        return candidate

    counter = 2
    while True:
        candidate = f"{base}_{fiscal_code}_{counter}.pdf"
        if candidate not in used_filenames:
            used_filenames.add(candidate)
            return candidate
        counter += 1


def write_pdf_slice(reader: PdfReader, output_path: Path, start_page: int, end_page: int) -> None:
    writer = PdfWriter()
    for index in range(start_page, end_page + 1):
        writer.add_page(reader.pages[index])
    with output_path.open("wb") as handle:
        writer.write(handle)


def split_cud_pdf(
    input_pdf: Path,
    output_dir: Path,
    save_cover: bool = True,
    reporter: Callable[[str], None] | None = None,
) -> tuple[Path | None, list[EmployeeCudBlock]]:
    input_pdf = input_pdf.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()

    if not input_pdf.exists():
        raise FileNotFoundError(f"File PDF non trovato: {input_pdf}")

    output_dir.mkdir(parents=True, exist_ok=True)
    log = reporter or (lambda _: None)
    document_label = detect_document_label(input_pdf)
    reader = PdfReader(str(input_pdf))

    log(f"Analisi del PDF: {input_pdf.name}")
    front_pages, blocks = build_blocks(reader, document_label)
    log(f"Trovate {len(blocks)} certificazioni dipendente")

    cover_path: Path | None = None
    if save_cover and front_pages > 0:
        cover_path = output_dir / f"00_FRONTESPIZIO_{slug_for_filename(document_label)}.pdf"
        write_pdf_slice(reader, cover_path, 0, front_pages - 1)
        log(f"Frontespizio salvato: {cover_path.name}")

    for index, block in enumerate(blocks, start=1):
        output_path = output_dir / block.output_filename
        write_pdf_slice(reader, output_path, block.start_page, block.end_page)
        log(
            f"[{index:02d}/{len(blocks):02d}] {block.surname} {block.name} - "
            f"pagine {block.start_page + 1}-{block.end_page + 1} -> {output_path.name}"
        )

    return cover_path, blocks


class SanVincenzoCudApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("San Vincenzo CUD")
        self.root.geometry("880x620")
        self.root.minsize(820, 560)

        self.input_var = tk.StringVar(value=str(DEFAULT_INPUT if DEFAULT_INPUT.exists() else ""))
        self.output_var = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.cover_var = tk.BooleanVar(value=True)
        self.auto_open_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Pronto")

        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()
        self.root.after(100, self._poll_log_queue)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=16)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="San Vincenzo CUD", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Divide il PDF CU unico in file separati per dipendente e li rinomina automaticamente.",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        body = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        files_frame = ttk.LabelFrame(body, text="Percorsi", padding=12)
        files_frame.grid(row=0, column=0, sticky="ew")
        files_frame.columnconfigure(1, weight=1)

        ttk.Label(files_frame, text="PDF sorgente").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.Entry(files_frame, textvariable=self.input_var).grid(row=0, column=1, sticky="ew", pady=(0, 8))
        ttk.Button(files_frame, text="Sfoglia", command=self._browse_input).grid(row=0, column=2, padx=(8, 0), pady=(0, 8))

        ttk.Label(files_frame, text="Cartella output").grid(row=1, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(files_frame, textvariable=self.output_var).grid(row=1, column=1, sticky="ew")
        ttk.Button(files_frame, text="Scegli", command=self._browse_output).grid(row=1, column=2, padx=(8, 0))

        options_frame = ttk.LabelFrame(body, text="Opzioni", padding=12)
        options_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))

        ttk.Checkbutton(options_frame, text="Salva anche il frontespizio aziendale", variable=self.cover_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options_frame, text="Apri la cartella di output a fine elaborazione", variable=self.auto_open_var).grid(row=1, column=0, sticky="w", pady=(6, 0))

        log_frame = ttk.LabelFrame(body, text="Log", padding=12)
        log_frame.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_widget = tk.Text(log_frame, height=18, wrap="word", state="disabled")
        self.log_widget.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_widget.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(self.root, padding=16)
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        self.run_button = ttk.Button(footer, text="Dividi PDF", command=self._start_processing)
        self.run_button.grid(row=0, column=1, padx=(8, 0))

    def _browse_input(self) -> None:
        selected = filedialog.askopenfilename(
            title="Seleziona il PDF CU",
            filetypes=[("PDF", "*.pdf"), ("Tutti i file", "*.*")],
        )
        if selected:
            self.input_var.set(selected)

    def _browse_output(self) -> None:
        selected = filedialog.askdirectory(title="Scegli la cartella di output")
        if selected:
            self.output_var.set(selected)

    def _start_processing(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        input_pdf = Path(self.input_var.get().strip())
        output_dir = Path(self.output_var.get().strip())

        if not input_pdf.exists():
            messagebox.showerror("San Vincenzo CUD", "Il PDF indicato non esiste.")
            return

        if not output_dir:
            messagebox.showerror("San Vincenzo CUD", "Seleziona una cartella di output.")
            return

        self._append_log(f"Avvio elaborazione di {input_pdf.name}")
        self.status_var.set("Elaborazione in corso...")
        self.run_button.configure(state="disabled")

        self.worker = threading.Thread(
            target=self._run_processing,
            args=(input_pdf, output_dir, self.cover_var.get(), self.auto_open_var.get()),
            daemon=True,
        )
        self.worker.start()

    def _run_processing(self, input_pdf: Path, output_dir: Path, save_cover: bool, auto_open: bool) -> None:
        try:
            cover_path, blocks = split_cud_pdf(
                input_pdf=input_pdf,
                output_dir=output_dir,
                save_cover=save_cover,
                reporter=self._queue_log,
            )
            message = f"Completato: {len(blocks)} file dipendente creati"
            if cover_path:
                message += " + frontespizio"
            self.log_queue.put(("done", message))
            if auto_open and output_dir.exists():
                os.startfile(str(output_dir))
        except Exception as exc:  # pragma: no cover - gestione UI
            self.log_queue.put(("error", str(exc)))

    def _queue_log(self, message: str) -> None:
        self.log_queue.put(("log", message))

    def _poll_log_queue(self) -> None:
        while True:
            try:
                kind, message = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self._append_log(message)
            elif kind == "done":
                self._append_log(message)
                self.status_var.set(message)
                self.run_button.configure(state="normal")
                messagebox.showinfo("San Vincenzo CUD", message)
            elif kind == "error":
                self._append_log(f"ERRORE: {message}")
                self.status_var.set("Errore durante l'elaborazione")
                self.run_button.configure(state="normal")
                messagebox.showerror("San Vincenzo CUD", message)

        self.root.after(100, self._poll_log_queue)

    def _append_log(self, message: str) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", f"{message}\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def run(self) -> None:
        self.root.mainloop()


def format_summary(blocks: Iterable[EmployeeCudBlock]) -> str:
    blocks = list(blocks)
    if not blocks:
        return "Nessun file generato"
    first = blocks[0]
    last = blocks[-1]
    return (
        f"Creati {len(blocks)} file. "
        f"Primo: {first.output_filename}. Ultimo: {last.output_filename}."
    )


def run_cli(args: argparse.Namespace) -> int:
    input_pdf = Path(args.input)
    output_dir = Path(args.output)

    def report(message: str) -> None:
        print(message)

    cover_path, blocks = split_cud_pdf(
        input_pdf=input_pdf,
        output_dir=output_dir,
        save_cover=not args.skip_cover,
        reporter=report,
    )
    print(format_summary(blocks))
    if cover_path:
        print(f"Frontespizio: {cover_path.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Divide il PDF CU di San Vincenzo in file per dipendente")
    parser.add_argument("--input", help="PDF da dividere")
    parser.add_argument("--output", help="Cartella in cui salvare i file")
    parser.add_argument("--skip-cover", action="store_true", help="Non salvare il frontespizio aziendale")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.input and args.output:
        return run_cli(args)

    app = SanVincenzoCudApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())