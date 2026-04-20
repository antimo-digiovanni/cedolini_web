from pathlib import Path
import sys


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from turni_app.app import main
else:
    from .app import main


if __name__ == "__main__":
    raise SystemExit(main())