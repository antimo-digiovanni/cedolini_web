from django.urls import path
from . import views

urlpatterns = [

    # Area Dipendente
    path('', views.dashboard, name='dashboard'),
    path('p/<int:payslip_id>/', views.open_payslip, name='open_payslip'),

    # Registrazione
    path('register/<str:token>/', views.register_view, name='register_view'),

    # ------------------------
    # AREA ADMIN CUSTOM
    # ------------------------

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('admin-employees/', views.admin_employees, name='admin_employees'),
    path('admin-reset-password/<int:user_id>/', views.admin_reset_password, name='admin_reset_password'),
    path('admin-generate-link/<int:user_id>/', views.admin_generate_link, name='admin_generate_link'),

    path('admin-upload/', views.admin_upload_payslip, name='admin_upload_payslip'),
    path('admin-upload-folder-period/', views.admin_upload_period_folder, name='admin_upload_period_folder'),
    path('admin-report/', views.admin_report, name='admin_report'),
    path('admin-audit/', views.admin_audit_dashboard, name='admin_audit_dashboard'),
]