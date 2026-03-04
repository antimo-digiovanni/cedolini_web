from django.conf import settings

from storages.backends.s3boto3 import S3Boto3Storage


class R2PublicStorage(S3Boto3Storage):
    """Storage backend per Cloudflare R2 con URL pubblici.

    Usa le credenziali / endpoint S3 standard per leggere/scrivere
    ma genera URL pubblici basati su R2_PUBLIC_BASE_URL, nel formato:

        https://<dominio-pubblico>/<bucket>/<percorso-file>
    """

    def url(self, name, parameters=None, expire=None, http_method=None):  # type: ignore[override]
        base_url = getattr(settings, "R2_PUBLIC_BASE_URL", None)

        if base_url:
            base_url = base_url.rstrip("/")
            name = name.lstrip("/")
            # Il dominio R2 pubblico punta già alla root del bucket,
            # quindi non aggiungiamo il nome del bucket nel path.
            return f"{base_url}/{name}"

        # Fallback: comportamento standard S3Boto3Storage
        return super().url(name, parameters=parameters, expire=expire, http_method=http_method)
