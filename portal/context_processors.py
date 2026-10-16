from .access import (
    user_has_full_admin_access,
    user_has_patrimonio_access,
    user_has_turni_planner_access,
    user_has_today_markings_access,
    user_has_today_markings_only_access,
    user_home_url_name,
)


def dpi_pending(request):
    """Numero di consegne DPI che il dipendente deve ancora firmare (per menu e avviso)."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or user.is_staff:
        return {"dpi_pending_count": 0}
    from .models import DPI_STATUS_PENDING, DpiDelivery
    return {"dpi_pending_count": DpiDelivery.objects.filter(employee__user=user, status=DPI_STATUS_PENDING).count()}


def portal_access(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {
            "has_full_admin_access": False,
            "has_patrimonio_access": False,
            "has_turni_planner_access": False,
            "has_today_markings_access": False,
            "has_today_markings_only_access": False,
            "portal_home_url_name": "dashboard",
        }

    return {
        "has_full_admin_access": user_has_full_admin_access(user),
        "has_patrimonio_access": user_has_patrimonio_access(user),
        "has_turni_planner_access": user_has_turni_planner_access(user),
        "has_today_markings_access": user_has_today_markings_access(user),
        "has_today_markings_only_access": user_has_today_markings_only_access(user),
        "portal_home_url_name": user_home_url_name(user),
    }