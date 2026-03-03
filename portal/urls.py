from django.urls import path
from . import views

urlpatterns = [

    path('', views.dashboard, name='dashboard'),

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    path('admin-upload-folder-period/', views.admin_upload_period_folder, name='admin_upload_period_folder'),

    path('import-progress/<int:job_id>/', views.import_progress, name='import_progress'),

    path('open/<int:payslip_id>/', views.open_payslip, name='open_payslip'),

]