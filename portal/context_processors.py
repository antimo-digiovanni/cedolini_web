from .access import (
    user_has_full_admin_access,
    user_has_smart_agenda_access,
    user_has_turni_planner_access,
    user_has_today_markings_access,
    user_home_url_name,
)


def portal_access(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {
            "has_full_admin_access": False,
            "has_smart_agenda_access": False,
            "has_turni_planner_access": False,
            "has_today_markings_access": False,
            "portal_home_url_name": "dashboard",
        }

    return {
        "has_full_admin_access": user_has_full_admin_access(user),
        "has_smart_agenda_access": user_has_smart_agenda_access(user),
        "has_turni_planner_access": user_has_turni_planner_access(user),
        "has_today_markings_access": user_has_today_markings_access(user),
        "portal_home_url_name": user_home_url_name(user),
    }