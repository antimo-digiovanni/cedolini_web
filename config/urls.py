from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from portal import views

urlpatterns = [

    # Django Admin
    path('admin/', admin.site.urls),

    # Home
    path('', views.home, name='home'),
    path('chi-siamo/', views.public_about, name='public_about'),
    path('servizi/', views.public_services, name='public_services'),
    path('macchinari/', views.public_machinery, name='public_machinery'),
    path('contatti/', views.public_contacts, name='public_contacts'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),
    path('robots.txt', views.robots_txt, name='robots_txt'),

    # Login / Logout
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Cambio password (QUESTO RISOLVE L'ERRORE)
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html'
    ), name='password_change'),

    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),

    # Portal app
    path('portal/', include('portal.urls')),
]