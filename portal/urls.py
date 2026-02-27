from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from portal import views  # <--- CORREZIONE: importa da portal

urlpatterns = [
    # Pannello di amministrazione Django
    path("admin/", admin.site.urls),

    # Home e logiche principali
    path("", views.home, name="home"),
    path("check-password/", views.force_password_change_if_needed, name="check_password"),
    path("p/<int:payslip_id>/", views.open_payslip, name="open_payslip"),

    # ✅ Completa profilo
    path("complete-profile/", views.complete_profile, name="complete_profile"),

    # ✅ Attivazione invito
    path("activate/<uidb64>/<token>/", views.activate_account, name="activate_account"),

    # Admin personalizzati
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-report/", views.admin_report, name="admin_report"),
    path("admin-audit/", views.admin_audit_dashboard, name="admin_audit_dashboard"),

    # Upload e gestione
    path("admin-upload/", views.admin_upload_payslip, name="admin_upload_payslip"),
    path("admin-upload-folder-period/", views.admin_upload_period_folder, name="admin_upload_period_folder"),
    path("admin-manage/", views.admin_manage_employees, name="admin_manage_employees"),
    path("admin-manage/<int:employee_id>/", views.admin_employee_payslips, name="admin_employee_payslips"),
    path("admin-payslip/<int:payslip_id>/reset-view/", views.admin_reset_payslip_view, name="admin_reset_payslip_view"),
    path("admin-payslip/<int:payslip_id>/delete/", views.admin_delete_payslip, name="admin_delete_payslip"),

    # Auth
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # Password
    path("password-change/", views.portal_set_password, name="password_change"),
    path("password-change/done/", views.portal_set_password_done, name="password_change_done"),

    # Reset password
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html",
        email_template_name="registration/password_reset_email.html",
        extra_email_context={
            "DEFAULT_DOMAIN": settings.DEFAULT_DOMAIN,
            "DEFAULT_PROTOCOL": settings.DEFAULT_PROTOCOL,
        },
    ), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="registration/password_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
]