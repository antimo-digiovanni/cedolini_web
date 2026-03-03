from django.urls import path
from . import views

urlpatterns = [
    # Dashboard admin
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Upload cedolini
    path('admin-upload/', views.admin_upload_period_folder, name='admin_upload_period_folder'),

    # Lista cedolini utente
    path('payslips/', views.payslip_list, name='payslip_list'),

    # Download cedolino
    path('payslip/<int:pk>/download/', views.payslip_download, name='payslip_download'),
]