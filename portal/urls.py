from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('p/<int:payslip_id>/', views.open_payslip, name='open_payslip'),

    # Admin
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-upload/', views.admin_upload_payslip, name='admin_upload_payslip'),
    path('admin-upload-folder-period/', views.admin_upload_period_folder, name='admin_upload_period_folder'),
    path('admin-report/', views.admin_report, name='admin_report'),
    path('admin-audit/', views.admin_audit_dashboard, name='admin_audit_dashboard'),

    # Test Email
    path('test-email/', views.test_email, name='test_email'),
]