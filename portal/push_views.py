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
