from django.contrib.auth.models import Group


TODAY_MARKINGS_GROUP_NAME = "titolare_solo_marcature_oggi"
TURNI_PLANNER_GROUP_NAME = "turni_planner_users"


def user_has_full_admin_access(user):
    return bool(getattr(user, "is_authenticated", False) and user.is_staff)


def user_has_today_markings_access(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return Group.objects.filter(
        name=TODAY_MARKINGS_GROUP_NAME,
        user=user,
    ).exists()


def user_has_today_markings_only_access(user):
    if not user_has_today_markings_access(user):
        return False
    if user_has_full_admin_access(user):
        return False
    return not hasattr(user, "employee")


def user_has_turni_planner_access(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff:
        return True
    return Group.objects.filter(
        name=TURNI_PLANNER_GROUP_NAME,
        user=user,
    ).exists()

def user_home_url_name(user):
    if user_has_full_admin_access(user):
        return "admin_dashboard"
    if user_has_turni_planner_access(user):
        return "turni_planner_home"
    if user_has_today_markings_only_access(user):
        return "today_markings_dashboard"
    return "dashboard"