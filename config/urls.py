from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from portal import views
from portal import group_gateway
from portal import public_site
from django.views.generic import TemplateView

urlpatterns = [

    # Django Admin
    path('admin/', admin.site.urls),

    # Home
    path('', public_site.home, name='home'),
    path('gruppo/', group_gateway.group_home, name='group_home'),
    path('gruppo/<path:filename>', group_gateway.group_asset, name='group_asset'),
    path('azienda/san-vincenzo/', group_gateway.select_san_vincenzo, name='select_san_vincenzo'),
    path('sito-web/', public_site.page, name='public_home'),
    path('disinfestazione-derattizzazione/', public_site.page, {'page':'disinfestazione-derattizzazione'}, name='public_pest_control'),
    path('chi-siamo/', public_site.page, {'page':'chi-siamo'}, name='public_about'),
    path('servizi/', public_site.page, {'page':'servizi'}, name='public_services'),
    path('servizi-digitali/', public_site.page, {'page':'servizi-digitali'}, name='public_digital_services'),
    path('macchinari/', public_site.page, {'page':'macchinari'}, name='public_machinery'),
    path('contatti/', public_site.page, {'page':'contatti'}, name='public_contacts'),
    path('san-vincenzo-assets/<str:filename>', public_site.asset, name='public_site_asset'),
    path('site.webmanifest', views.site_webmanifest, name='site_webmanifest'),
    path('manifest.webmanifest', views.site_webmanifest, name='site_webmanifest_alias'),
    path('employee-app.webmanifest', views.employee_webmanifest, name='employee_webmanifest'),
    path('service-worker.js', views.service_worker, name='service_worker'),
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
