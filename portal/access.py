from django.contrib.auth.models import Group


TODAY_MARKINGS_GROUP_NAME = "titolare_solo_marcature_oggi"


def user_has_full_admin_access(user):
    return bool(getattr(user, "is_authenticated", False) and user.is_staff)


def user_has_today_markings_access(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return Group.objects.filter(
        name=TODAY_MARKINGS_GROUP_NAME,
        user=user,
    ).exists()


def user_home_url_name(user):
    if user_has_full_admin_access(user):
        return "admin_dashboard"
    if user_has_today_markings_access(user):
        return "today_markings_dashboard"
    return "dashboard"