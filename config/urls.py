from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from portal import views

urlpatterns = [

    # Django Admin
    path('admin/', admin.site.urls),

    # Home
    path('', views.home, name='home'),
    path('sito-web/', views.public_home, name='public_home'),
    path('chi-siamo/', views.public_about, name='public_about'),
    path('servizi/', views.public_services, name='public_services'),
    path('servizi-digitali/', views.public_digital_services, name='public_digital_services'),
    path('macchinari/', views.public_machinery, name='public_machinery'),
    path('contatti/', views.public_contacts, name='public_contacts'),
    path('site.webmanifest', views.site_webmanifest, name='site_webmanifest'),
    path('manifest.webmanifest', views.site_webmanifest, name='site_webmanifest_alias'),
    path('favicon.ico', views.favicon_ico, name='favicon_ico'),
    path('favicon-32x32.png', views.favicon_32_png, name='favicon_32_png'),
    path('favicon-16x16.png', views.favicon_16_png, name='favicon_16_png'),
    path('apple-touch-icon.png', views.apple_touch_icon, name='apple_touch_icon'),
    path('apple-touch-icon-precomposed.png', views.apple_touch_icon_precomposed, name='apple_touch_icon_precomposed'),
    path('googlee8ce7f16b7b5fed5.html', views.google_site_verification, name='google_site_verification'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),
    path('robots.txt', views.robots_txt, name='robots_txt'),

    # Login / Logout
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Recupero password
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        success_url='/password-reset/done/'
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url='/reset/done/'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

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