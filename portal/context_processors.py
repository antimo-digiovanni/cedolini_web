from .access import (
    user_has_full_admin_access,
    user_has_patrimonio_access,
    user_has_turni_planner_access,
    user_has_today_markings_access,
    user_has_today_markings_only_access,
    user_home_url_name,
)


def dpi_pending(request):
    """Numero di consegne DPI che l'utente deve ancora firmare come dipendente (anche se è admin)."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"dpi_pending_count": 0}
    from .models import DPI_STATUS_PENDING, DpiDelivery
    try:
        from .identity_docs import maybe_run_daily_checks
        maybe_run_daily_checks()
    except Exception:
        pass
    ctx = {"dpi_pending_count": DpiDelivery.objects.filter(employee__user=user, status=DPI_STATUS_PENDING).count()}
    # Avvisi documenti di identità: solo sulla dashboard dipendente, per non appesantire le altre pagine.
    match = getattr(request, "resolver_match", None)
    if match and match.url_name == "dashboard":
        try:
            from .identity_docs import needs_attention
            from .models import Employee
            emp = Employee.objects.filter(user=user).first()
            ctx["doc_alerts"] = needs_attention(emp) if emp else []
        except Exception:
            ctx["doc_alerts"] = []
    return ctx


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