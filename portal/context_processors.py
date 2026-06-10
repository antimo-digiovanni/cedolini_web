from .access import (
    user_has_full_admin_access,
    user_has_riconfezionamento_access,
    user_has_turni_planner_access,
    user_has_today_markings_access,
    user_has_today_markings_only_access,
    user_home_url_name,
)


def portal_access(request):
    user = getattr(request, "user", None)
    riconfezionamento_online_enabled = getattr(settings, "RICONFEZIONAMENTO_ONLINE_ENABLED", False)
    if user is None or not user.is_authenticated:
        return {
            "has_full_admin_access": False,
            "has_riconfezionamento_access": False,
            "riconfezionamento_online_enabled": riconfezionamento_online_enabled,
            "has_turni_planner_access": False,
            "has_today_markings_access": False,
            "has_today_markings_only_access": False,
            "portal_home_url_name": "dashboard",
        }

    return {
        "has_full_admin_access": user_has_full_admin_access(user),
        "has_riconfezionamento_access": riconfezionamento_online_enabled and user_has_riconfezionamento_access(user),
        "riconfezionamento_online_enabled": riconfezionamento_online_enabled,
        "has_turni_planner_access": user_has_turni_planner_access(user),
        "has_today_markings_access": user_has_today_markings_access(user),
        "has_today_markings_only_access": user_has_today_markings_only_access(user),
        "portal_home_url_name": user_home_url_name(user),
    }