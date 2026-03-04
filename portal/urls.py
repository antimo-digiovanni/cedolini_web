from django.urls import path
from . import views

urlpatterns = [

    path('', views.dashboard, name='dashboard'),

    path('register/<str:token>/', views.register_with_token, name='register_with_token'),

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-upload-cud/', views.admin_upload_cud, name='admin_upload_cud'),
    path('admin-report/', views.admin_report, name='admin_report'),
    path('admin-all-payslips/', views.admin_all_payslips, name='admin_all_payslips'),
    path('admin-audit-events/', views.admin_audit_events, name='admin_audit_events'),
    path('admin-import-jobs/', views.admin_import_jobs, name='admin_import_jobs'),
    path('admin-import-jobs/<int:job_id>/payslips/', views.admin_import_job_payslips, name='admin_import_job_payslips'),
    path('admin-employees/', views.admin_employees, name='admin_employees'),
    path('admin-payslip-integrity/', views.admin_payslip_integrity, name='admin_payslip_integrity'),
    path('admin-send-invite/', views.admin_send_invite, name='admin_send_invite'),
    path('admin-employee/<int:emp_id>/', views.admin_employee_detail, name='admin_employee_detail'),
    path('admin-employee-payslips/<int:emp_id>/', views.admin_employee_payslips, name='admin_employee_payslips'),
    path('admin-reset-payslip-view/<int:payslip_id>/', views.admin_reset_payslip_view, name='admin_reset_payslip_view'),

    # Admin upload folder/zip: ripristinato
    path('admin-upload-folder-period/', views.admin_upload_period_folder, name='admin_upload_period_folder'),
    path('admin-cancel-import/', views.admin_cancel_import, name='admin_cancel_import'),

    path('open/<int:payslip_id>/', views.open_payslip, name='open_payslip'),
    path('cud/<int:cud_id>/', views.open_cud, name='open_cud'),
]