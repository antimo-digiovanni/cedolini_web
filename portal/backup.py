"""Copia di sicurezza giornaliera del database su Cloudflare R2 (cartella privata «backup/»).

Ogni giorno viene salvato un file JSON compresso (formato di `manage.py dumpdata`), con un nome
non indovinabile; si tengono gli ultimi KEEP_DAYS giorni. Per ripristinare: scaricare il file
da R2, decomprimerlo e usare `python manage.py loaddata <file>.json` su un database vuoto.
"""

import gzip
import logging
import os
import secrets
import tempfile

from django.conf import settings
from django.core.files import File
from django.utils import timezone

logger = logging.getLogger(__name__)

FOLDER = 'backup'
KEEP_DAYS = 30
EXCLUDE = ['contenttypes', 'auth.permission', 'sessions', 'admin.logentry', 'portal.loginthrottle']


def enabled():
    return bool(getattr(settings, 'AWS_S3_ENDPOINT_URL', None) and getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None))


def run_backup():
    from django.core.files.storage import default_storage
    from django.core.management import call_command

    if not enabled():
        return None
    today = timezone.localdate()
    fd, raw_path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    gz_path = raw_path + '.gz'
    try:
        call_command('dumpdata', exclude=EXCLUDE, natural_foreign=True, output=raw_path, verbosity=0)
        with open(raw_path, 'rb') as src, gzip.open(gz_path, 'wb', compresslevel=6) as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
        name = f'{FOLDER}/db-{today:%Y-%m-%d}-{secrets.token_hex(12)}.json.gz'
        with open(gz_path, 'rb') as fh:
            saved = default_storage.save(name, File(fh))
        logger.info('backup database salvato: %s (%d KB)', saved, os.path.getsize(gz_path) // 1024)
        _cleanup(default_storage, today)
        return saved
    finally:
        for p in (raw_path, gz_path):
            try:
                os.remove(p)
            except OSError:
                pass


def _cleanup(storage, today):
    from datetime import date, timedelta

    limit = today - timedelta(days=KEEP_DAYS)
    try:
        _, files = storage.listdir(FOLDER)
    except Exception:
        logger.exception('backup: impossibile elencare i vecchi backup')
        return
    for f in files:
        try:
            day = date.fromisoformat(f[3:13])  # db-AAAA-MM-GG-...
        except ValueError:
            continue
        if day < limit:
            try:
                storage.delete(f'{FOLDER}/{f}')
            except Exception:
                logger.exception('backup: impossibile eliminare %s', f)
