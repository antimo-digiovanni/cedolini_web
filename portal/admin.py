from django.contrib import admin
from django.db.models import Exists, OuterRef

from .models import Employee, Payslip, PayslipView, AuditEvent


class ViewedFilter(admin.SimpleListFilter):
    title = "Visualizzazione"
    parameter_name = "viewed"

    def lookups(self, request, model_admin):
        return (("yes", "Visualizzati"), ("no", "Non visualizzati"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(view__isnull=False)
        if self.value() == "no":
            return queryset.filter(view__isnull=True)
        return queryset


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "external_code", "user", "must_change_password")
    search_fields = ("full_name", "external_code", "user__username", "user__email")
    autocomplete_fields = ("user",)
    list_filter = ("must_change_password", "external_code")
    fields = ("user", "full_name", "external_code", "must_change_password")
    ordering = ("full_name", "external_code", "id")


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ("employee", "month", "year", "uploaded_at", "is_viewed", "viewed_at")
    list_filter = (ViewedFilter, "year", "month")
    search_fields = ("employee__full_name", "employee__user__username", "employee__user__email")
    ordering = ("-year", "-month", "employee__full_name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_view_exists=Exists(PayslipView.objects.filter(payslip=OuterRef("pk"))))

    @admin.display(boolean=True, description="Visualizzato")
    def is_viewed(self, obj):
        return getattr(obj, "_view_exists", False)

    @admin.display(description="Data visualizzazione")
    def viewed_at(self, obj):
        if hasattr(obj, "view") and obj.view:
            return obj.view.viewed_at
        return "-"


@admin.register(PayslipView)
class PayslipViewAdmin(admin.ModelAdmin):
    list_display = ("payslip", "viewed_at")
    list_filter = ("viewed_at",)
    search_fields = ("payslip__employee__full_name",)
    ordering = ("-viewed_at",)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "employee", "payslip", "actor_user", "ip_address")
    list_filter = ("action", "created_at")
    search_fields = ("employee__full_name", "payslip__employee__full_name", "actor_user__username", "ip_address")
    ordering = ("-created_at",)