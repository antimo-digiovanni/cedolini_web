from django.contrib import admin
from django.urls import path, include
from portal import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Account e Registrazione
    path('register/<str:token>/', views.register_view, name='register'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate_account'),
    path('check-password/', views.force_password_change_if_needed, name='check_password'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    
    # Dashboard e Report
    path('p/<int:payslip_id>/', views.open_payslip, name='open_payslip'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-report/', views.admin_report, name='admin_report'),
    path('admin-audit/', views.admin_audit_dashboard, name='admin_audit_dashboard'),
    
    path('portal/', include('portal.urls')),
]