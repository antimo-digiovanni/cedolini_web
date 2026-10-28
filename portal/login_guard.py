"""Protezione dell'accesso: blocco temporaneo dopo troppi tentativi con password sbagliata."""

import logging
import math
from datetime import timedelta

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

WINDOW = timedelta(minutes=15)
LOCK_FOR = timedelta(minutes=15)
MAX_PER_ACCOUNT = 8   # errori consecutivi sullo stesso account
MAX_PER_IP = 40       # alto: in cantiere molti telefoni escono dallo stesso indirizzo


def client_ip(request):
    if request is None:
        return ''
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()[:60]
    return (request.META.get('REMOTE_ADDR') or '')[:60]


def _keys(request, username):
    keys = []
    if username:
        keys.append((f'u:{username.strip().lower()[:150]}', MAX_PER_ACCOUNT))
    ip = client_ip(request)
    if ip:
        keys.append((f'ip:{ip}', MAX_PER_IP))
    return keys


def locked_minutes(request, username):
    """Minuti di blocco rimanenti (0 se si può provare)."""
    from .models import LoginThrottle

    now = timezone.now()
    keys = [k for k, _ in _keys(request, username)]
    worst = None
    for row in LoginThrottle.objects.filter(key__in=keys, locked_until__gt=now):
        if worst is None or row.locked_until > worst:
            worst = row.locked_until
    if worst is None:
        return 0
    return max(1, math.ceil((worst - now).total_seconds() / 60))


def register_failure(request, username):
    from .models import LoginThrottle

    now = timezone.now()
    for key, limit in _keys(request, username):
        with transaction.atomic():
            row, _ = LoginThrottle.objects.select_for_update().get_or_create(
                key=key, defaults={'window_start': now})
            if row.window_start < now - WINDOW and not (row.locked_until and row.locked_until > now):
                row.failures = 0
                row.window_start = now
            row.failures += 1
            if row.failures >= limit:
                row.locked_until = now + LOCK_FOR
                row.failures = 0
                row.window_start = now
                logger.warning('accesso bloccato per 15 minuti: %s', key)
            row.save()


def register_success(request, username):
    from .models import LoginThrottle

    LoginThrottle.objects.filter(key__in=[k for k, _ in _keys(request, username) if k.startswith('u:')]).delete()


class GuardedAuthenticationForm(AuthenticationForm):
    """Login con username o email; dopo troppi errori l'accesso si blocca per qualche minuto."""

    locked_for = 0

    def clean(self):
        username = self.cleaned_data.get('username') or ''
        try:
            self.locked_for = locked_minutes(self.request, username)
        except Exception:
            logger.exception('controllo tentativi di accesso non riuscito')
            self.locked_for = 0
        if self.locked_for:
            raise forms.ValidationError('Troppi tentativi non riusciti.', code='locked')
        try:
            cleaned = super().clean()
        except forms.ValidationError as exc:
            if getattr(exc, 'code', None) == 'invalid_login':
                try:
                    register_failure(self.request, username)
                    self.locked_for = locked_minutes(self.request, username)
                except Exception:
                    logger.exception('registrazione tentativo fallito non riuscita')
            raise
        try:
            register_success(self.request, username)
        except Exception:
            logger.exception('azzeramento tentativi non riuscito')
        return cleaned
