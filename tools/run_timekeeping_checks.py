import os
from pathlib import Path
import sys
import tempfile


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    with tempfile.TemporaryDirectory(prefix="cedolini-timekeeping-tests-") as temporary:
        os.environ["APP_RICONFEZIONAMENTO_DATA_DIR"] = temporary
        os.environ["APP_RICONFEZIONAMENTO_PRODUCTS_XLSX"] = str(Path(temporary) / "Prodotti.xlsx")
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
        from django.conf import settings
        settings.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        settings.MEDIA_ROOT = str(Path(temporary) / "media")
        settings.STORAGES = {
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
        import django
        django.setup()
        from django.core.management import call_command
        call_command(
            "test", "portal.test_timekeeping_multiple", "portal.tests.VacationRequestFlowTests",
            "portal.tests.TimekeepingAjaxGeolocationTests", "portal.tests.TodayMarkingsAccessTests",
            "portal.test_portal_theme",
            verbosity=1, interactive=False,
        )
        call_command("makemigrations", "portal", check=True, dry_run=True)


if __name__ == "__main__":
    main()