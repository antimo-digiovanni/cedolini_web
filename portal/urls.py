from django.urls import path
from . import views

urlpatterns = [

    path('', views.dashboard, name='dashboard'),

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-employees/', views.admin_employees, name='admin_employees'),
    path('admin-employees/<int:employee_id>/', views.admin_employee_detail, name='admin_employee_detail'),

    path('admin-upload-folder-period/', views.admin_upload_period_folder, name='admin_upload_period_folder'),
    path('admin-upload/', views.admin_upload_payslip, name='admin_upload_payslip'),
    path('admin-audit/', views.admin_audit_dashboard, name='admin_audit_dashboard'),

    path('open/<int:payslip_id>/', views.open_payslip, name='open_payslip'),

    path('register/<str:token>/', views.register_view, name='register_view'),
]