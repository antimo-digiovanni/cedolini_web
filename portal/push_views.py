import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from . import push
from .models import PushSubscription


@login_required
@require_GET
def push_public_key(request):
    _, public_key = push.get_keys()
    return JsonResponse({'key': public_key})


@login_required
@require_POST
def push_subscribe(request):
    try:
        data = json.loads(request.body or b'{}')
        endpoint = str(data['endpoint'])
        keys = data['keys']
        p256dh, auth = str(keys['p256dh']), str(keys['auth'])
    except (ValueError, KeyError, TypeError):
        return JsonResponse({'ok': False}, status=400)
    if not endpoint.startswith('https://') or len(endpoint) > 1000 or len(p256dh) > 255 or len(auth) > 255:
        return JsonResponse({'ok': False}, status=400)
    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth,
                  'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500]},
    )
    return JsonResponse({'ok': True})


@login_required
@require_POST
def push_unsubscribe(request):
    try:
        endpoint = str(json.loads(request.body or b'{}')['endpoint'])
    except (ValueError, KeyError, TypeError):
        return JsonResponse({'ok': False}, status=400)
    PushSubscription.objects.filter(endpoint=endpoint, user=request.user).delete()
    return JsonResponse({'ok': True})


# ------------------------------------------------------------------ amministrazione

NOTIF_FILTERS = {'tutti': 'Tutti', 'attive': 'Notifiche attive', 'non_attive': 'Notifiche non attive'}


@login_required
def admin_notifications(request):
    """Chi ha le notifiche attive e chi no, con i dispositivi e una notifica di prova."""
    from django.shortcuts import redirect, render
    from django.urls import reverse

    from .models import Employee

    if not request.user.is_staff:
        return redirect('dashboard')

    feedback = None
    if request.method == 'POST' and request.POST.get('action') == 'test':
        emp = Employee.objects.select_related('user').filter(id=request.POST.get('employee')).first()
        if emp:
            sent = push.send_to_user(emp.user, title='Notifica di prova',
                                     body='Le notifiche del portale San Vincenzo funzionano.',
                                     url=reverse('dashboard'), tag='prova')
            feedback = ('ok' if sent else 'ko', emp.full_name, sent)

    filtro = request.GET.get('filtro', 'tutti')
    if filtro not in NOTIF_FILTERS:
        filtro = 'tutti'
    q = (request.GET.get('q') or '').strip()

    employees = (Employee.objects.select_related('user').prefetch_related('user__push_subscriptions')
                 .filter(user__is_active=True).order_by('last_name', 'first_name'))
    rows, counts = [], {'attive': 0, 'non_attive': 0}
    for emp in employees:
        devices = push.describe_user_devices(emp.user)
        active = bool(devices)
        counts['attive' if active else 'non_attive'] += 1
        if filtro == 'attive' and not active or filtro == 'non_attive' and active:
            continue
        if q and q.lower() not in f'{emp.first_name} {emp.last_name} {emp.last_name} {emp.first_name}'.lower():
            continue
        rows.append({'employee': emp, 'active': active, 'devices': devices,
                     'has_error': any(d['last_error'] for d in devices)})
    counts['tutti'] = counts['attive'] + counts['non_attive']
    return render(request, 'portal/admin_notifications.html', {
        'rows': rows, 'counts': counts, 'filters': NOTIF_FILTERS, 'filtro': filtro, 'q': q, 'feedback': feedback,
    })
