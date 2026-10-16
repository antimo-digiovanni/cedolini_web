"""Notifiche push (Web Push) verso i dispositivi dei dipendenti.

Le chiavi VAPID vengono generate al primo uso e salvate nel database,
così non serve configurare variabili d'ambiente.
"""

import base64
import json
import logging
import time

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

VAPID_SUBJECT = 'https://www.sanvincenzoservice.it'

SERVICE_WORKER_HANDLERS = r"""
self.addEventListener('push', (event) => {
    let data = {};
    try { data = event.data ? event.data.json() : {}; } catch (e) { data = { body: event.data && event.data.text() }; }
    const title = data.title || 'San Vincenzo';
    event.waitUntil(self.registration.showNotification(title, {
        body: data.body || '',
        icon: '/static/portal/icons/icon-192.png',
        badge: '/static/portal/icons/icon-192.png',
        tag: data.tag || 'portale',
        data: { url: data.url || '/portal/' }
    }));
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const target = new URL((event.notification.data && event.notification.data.url) || '/portal/', self.location.origin).href;
    event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
        for (const client of list) {
            if (client.url.startsWith(self.location.origin) && 'focus' in client) {
                return client.navigate(target).then((c) => (c || client).focus()).catch(() => client.focus());
            }
        }
        return clients.openWindow(target);
    }));
});
"""


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def get_keys():
    """Restituisce (private_pem, public_key_b64url), generandole se mancano."""
    from .models import WebPushKey

    key = WebPushKey.objects.order_by('id').first()
    if key:
        return key.private_pem, key.public_key

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    with transaction.atomic():
        key = WebPushKey.objects.select_for_update().order_by('id').first()
        if key:
            return key.private_pem, key.public_key
        private = ec.generate_private_key(ec.SECP256R1())
        pem = private.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        ).decode()
        public = private.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        key = WebPushKey.objects.create(private_pem=pem, public_key=_b64url(public))
        return key.private_pem, key.public_key


def _record_error(sub, message):
    sub.last_error = message[:300]
    sub.last_error_at = timezone.now()
    sub.save(update_fields=['last_error', 'last_error_at'])


def describe_user_devices(user):
    """Riepilogo leggibile dei dispositivi iscritti, per la diagnostica in pagina admin."""
    out = []
    for s in user.push_subscriptions.order_by('-created_at'):
        host = s.endpoint.split('/')[2] if s.endpoint.count('/') >= 2 else s.endpoint
        kind = 'iPhone/Safari' if 'apple.com' in host else ('Android/Chrome' if 'googleapis.com' in host else host)
        out.append({'kind': kind, 'created_at': s.created_at, 'last_success_at': s.last_success_at,
                    'last_error': s.last_error, 'last_error_at': s.last_error_at})
    return out


def recent_devices(limit=10):
    """Ultimi dispositivi iscritti in tutto il portale, con l'account a cui appartengono."""
    from .models import PushSubscription
    out = []
    for s in PushSubscription.objects.select_related('user').order_by('-created_at')[:limit]:
        name = s.user.get_full_name() or s.user.get_username()
        try:
            name = s.user.employee.full_name
        except Exception:
            pass
        host = s.endpoint.split('/')[2] if s.endpoint.count('/') >= 2 else s.endpoint
        kind = 'iPhone/Safari' if 'apple.com' in host else ('Android/Chrome' if 'googleapis.com' in host else host)
        out.append({'account': s.user.get_username(), 'name': name, 'is_staff': s.user.is_staff,
                    'kind': kind, 'created_at': s.created_at})
    return out


def send_to_user(user, *, title, body, url, tag='portale'):
    """Invia la notifica a tutti i dispositivi dell'utente. Restituisce quanti l'hanno ricevuta."""
    from py_vapid import Vapid02
    from pywebpush import WebPushException, webpush

    subs = list(user.push_subscriptions.all())
    if not subs:
        return 0
    try:
        private_pem, _ = get_keys()
        vapid = Vapid02.from_pem(private_pem.encode())
    except Exception:
        logger.exception('push: chiavi VAPID non disponibili')
        return 0

    payload = json.dumps({'title': title, 'body': body, 'url': url, 'tag': tag})
    delivered = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={'endpoint': sub.endpoint, 'keys': {'p256dh': sub.p256dh, 'auth': sub.auth}},
                data=payload,
                vapid_private_key=vapid,
                # Scadenza esplicita a 12 ore: Apple rifiuta i token con scadenza oltre le 24 ore.
                vapid_claims={'sub': VAPID_SUBJECT, 'exp': int(time.time()) + 12 * 3600},
                ttl=7 * 24 * 3600,
                timeout=8,
            )
        except WebPushException as exc:
            resp = getattr(exc, 'response', None)
            status = getattr(resp, 'status_code', None)
            if status in (404, 410):
                sub.delete()  # dispositivo non più valido (app disinstallata o permesso revocato)
                continue
            detail = (getattr(resp, 'text', '') or str(exc))[:200]
            logger.warning('push: invio fallito user=%s status=%s %s', user.pk, status, detail)
            _record_error(sub, f'{status or "errore"} {detail}'.strip())
            continue
        except Exception as exc:
            logger.exception('push: errore invio user=%s', user.pk)
            _record_error(sub, f'{type(exc).__name__}: {exc}'[:300])
            continue
        delivered += 1
        sub.last_success_at = timezone.now()
        sub.last_error = ''
        sub.save(update_fields=['last_success_at', 'last_error'])
    return delivered


MONTHS_IT = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio',
             'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']


def notify_later(user_id, **message):
    """Invia la notifica dopo il salvataggio, in background, per non rallentare i caricamenti massivi."""
    from django.conf import settings
    from django.db import connection, transaction as tx

    def run():
        from django.contrib.auth import get_user_model
        try:
            user = get_user_model().objects.filter(pk=user_id).first()
            if user:
                send_to_user(user, **message)
        except Exception:
            logger.exception('push: errore notifica user=%s', user_id)
        finally:
            if getattr(settings, 'PUSH_ASYNC', True):
                connection.close()

    def start():
        if getattr(settings, 'PUSH_ASYNC', True):
            import threading
            threading.Thread(target=run, daemon=True).start()
        else:
            run()

    tx.on_commit(start)


def notify_payslip(payslip):
    from django.urls import reverse
    month = MONTHS_IT[payslip.month - 1] if 1 <= payslip.month <= 12 else str(payslip.month)
    notify_later(
        payslip.employee.user_id,
        title='Nuovo cedolino disponibile',
        body=f'È disponibile il tuo cedolino di {month} {payslip.year}. Tocca per aprirlo.',
        url=reverse('open_payslip', args=[payslip.id]),
        tag=f'cedolino-{payslip.year}-{payslip.month}',
    )


def notify_cud(cud):
    from django.urls import reverse
    notify_later(
        cud.employee.user_id,
        title='Nuovo CUD disponibile',
        body=f'È disponibile il tuo CUD {cud.year}. Tocca per aprirlo.',
        url=reverse('open_cud', args=[cud.id]),
        tag=f'cud-{cud.year}',
    )
