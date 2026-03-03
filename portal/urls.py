from django.urls import path
from . import views

urlpatterns = [

    path('', views.dashboard, name='dashboard'),

    path('register/<str:token>/', views.register_with_token, name='register_with_token'),

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Admin upload folder/zip: ripristinato
    path('admin-upload-folder-period/', views.admin_upload_period_folder, name='admin_upload_period_folder'),

    path('open/<int:payslip_id>/', views.open_payslip, name='open_payslip'),
]