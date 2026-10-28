"""Promemoria di uscita: notifica a chi ha marcato l'entrata e non ancora l'uscita.

Fasce (ora di entrata -> finestra in cui arriva il promemoria):
  05:00-08:59  ->  17:00-18:00 dello stesso giorno
  11:00-13:59  ->  22:00-23:00 dello stesso giorno
  21:00-23:59  ->  06:00-07:00 del giorno dopo
Fuori da queste fasce nessun promemoria. Un solo promemoria per marcatura.
"""

import logging
import sys
import threading
import time
from datetime import datetime, time as dtime, timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

# (ora entrata da, ora entrata a esclusa) -> (inizio finestra, fine finestra, giorni dopo l'entrata)
EXIT_REMINDER_RULES = [
    ((5, 9), (dtime(17, 0), dtime(18, 0), 0)),
    ((11, 14), (dtime(22, 0), dtime(23, 0), 0)),
    ((21, 24), (dtime(6, 0), dtime(7, 0), 1)),
]
CHECK_EVERY_SECONDS = 300


def reminder_window(started_at):
    """Finestra (inizio, fine) del promemoria per un'entrata, oppure None se l'orario non è in nessuna fascia."""
    local = timezone.localtime(started_at)
    for (h_from, h_to), (w_start, w_end, plus_days) in EXIT_REMINDER_RULES:
        if h_from <= local.hour < h_to:
            day = local.date() + timedelta(days=plus_days)
            tz = timezone.get_current_timezone()
            return (timezone.make_aware(datetime.combine(day, w_start), tz),
                    timezone.make_aware(datetime.combine(day, w_end), tz))
    return None


def send_due_exit_reminders(now=None):
    """Invia i promemoria la cui finestra è in corso. Restituisce quanti ne ha inviati."""
    from django.urls import reverse

    from . import push
    from .models import ExitReminder, WorkSession

    now = now or timezone.now()
    open_sessions = (WorkSession.objects.select_related('employee__user')
                     .filter(day_type=WorkSession.DAY_TYPE_WORK, started_at__isnull=False, ended_at__isnull=True,
                             corrected_ended_at__isnull=True, exit_reminder__isnull=True,
                             started_at__gte=now - timedelta(hours=26)))
    sent = 0
    for session in open_sessions:
        window = reminder_window(session.effective_started_at())
        if not window or not (window[0] <= now < window[1]):
            continue
        reminder, created = ExitReminder.objects.get_or_create(session=session)
        if not created:
            continue  # già inviato da un altro processo
        entered = timezone.localtime(session.effective_started_at())
        reminder.delivered_devices = push.send_to_user(
            session.employee.user,
            title='Ricordati di marcare l\'uscita',
            body=f'Hai marcato l\'entrata alle {entered:%H:%M} ma non ancora l\'uscita. Tocca per marcarla.',
            url=reverse('timekeeping'), tag=f'uscita-{session.id}')
        reminder.save(update_fields=['delivered_devices'])
        sent += 1
    return sent


def _claim(name, every_seconds):
    """True se questo processo deve eseguire il controllo adesso (al massimo uno ogni N secondi in tutto il portale)."""
    from django.db import transaction

    from .models import PeriodicTaskRun

    now = timezone.now()
    with transaction.atomic():
        run, created = PeriodicTaskRun.objects.select_for_update().get_or_create(name=name, defaults={'last_run': now})
        if created:
            return True
        if (now - run.last_run).total_seconds() < every_seconds - 5:
            return False
        run.last_run = now
        run.save(update_fields=['last_run'])
        return True


def run_periodic_checks():
    try:
        if _claim('promemoria_uscita', CHECK_EVERY_SECONDS):
            send_due_exit_reminders()
    except Exception:
        logger.exception('promemoria uscita: errore nel controllo periodico')


_LAST_LOCAL_CHECK = 0.0


def maybe_run_from_request():
    """Riserva: se il controllo in background non gira (es. server appena riavviato), lo esegue una richiesta."""
    global _LAST_LOCAL_CHECK
    if not _is_web_server() or time.monotonic() - _LAST_LOCAL_CHECK < CHECK_EVERY_SECONDS:
        return
    _LAST_LOCAL_CHECK = time.monotonic()
    threading.Thread(target=_run_and_close, daemon=True).start()


def _run_and_close():
    from django.db import connection
    try:
        run_periodic_checks()
    finally:
        connection.close()


def _loop():
    time.sleep(30)  # lascia finire l'avvio del server
    while True:
        _run_and_close()
        time.sleep(CHECK_EVERY_SECONDS)


def _is_web_server():
    cmd = ' '.join(sys.argv)
    return 'gunicorn' in cmd or 'runserver' in cmd


def start_scheduler():
    """Avvia il controllo ogni 5 minuti solo quando gira il server web (non durante migrate, test, ecc.)."""
    if not _is_web_server():
        return
    threading.Thread(target=_loop, name='promemoria-uscita', daemon=True).start()
