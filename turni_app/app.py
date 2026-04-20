from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .ui import APP_NAME, MainWindow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Planner desktop per i turni di lavoro San Vincenzo")
    parser.add_argument("workbook", nargs="?", help="Percorso del file Excel dei turni")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("AntimoTools")

    workbook_path = Path(args.workbook) if args.workbook else None
    window = MainWindow(workbook_path=workbook_path)
    window.show()
    QTimer.singleShot(0, window.load_startup_workbook)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())