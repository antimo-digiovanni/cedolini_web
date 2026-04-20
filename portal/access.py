from django.conf import settings
from django.contrib.auth.models import Group


TODAY_MARKINGS_GROUP_NAME = "titolare_solo_marcature_oggi"


def _configured_smart_agenda_usernames():
    configured = getattr(settings, 'SMART_AGENDA_ALLOWED_USERNAMES', None)
    if configured:
        return {str(item).strip().lower() for item in configured if str(item).strip()}
    return {'antimo', 'antim'}


def user_has_full_admin_access(user):
    return bool(getattr(user, "is_authenticated", False) and user.is_staff)


def user_has_today_markings_access(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return Group.objects.filter(
        name=TODAY_MARKINGS_GROUP_NAME,
        user=user,
    ).exists()


def user_has_smart_agenda_access(user):
    if not getattr(user, 'is_authenticated', False):
        return False

    allowed_usernames = _configured_smart_agenda_usernames()
    username = (getattr(user, 'username', '') or '').strip().lower()
    email = (getattr(user, 'email', '') or '').strip().lower()
    email_local = email.split('@', 1)[0] if '@' in email else email
    first_name = (getattr(user, 'first_name', '') or '').strip().lower()

    if username in allowed_usernames:
        return True

    if any(email.startswith(f'{item}@') for item in allowed_usernames):
        return True

    if any(item in username for item in allowed_usernames):
        return True

    if any(item in email_local for item in allowed_usernames):
        return True

    return first_name == 'antimo'


def user_home_url_name(user):
    if user_has_full_admin_access(user):
        return "admin_dashboard"
    if user_has_today_markings_access(user):
        return "today_markings_dashboard"
    return "dashboard"