from pathlib import Path
import os
import dj_database_url  # Importante: serve per leggere l'URL del database di Render

# Base directory del progetto
BASE_DIR = Path(__file__).resolve().parent.parent

# La chiave segreta (in produzione, usa una variabile d'ambiente)
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-only-change-me")

# Accetta l'host di Render e i locali
ALLOWED_HOSTS = ['cedolini-web.onrender.com', 'localhost', '127.0.0.1']

# Configurazione del debug (setta a False in produzione)
DEBUG = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "portal",  # Assicurati che questa app sia configurata
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Per servire il logo e i CSS
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],  # Assicurati che la cartella templates esista
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# CONFIGURAZIONE DATABASE POSTGRESQL
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600
    )
}

if not DATABASES['default']:
    DATABASES['default'] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

# Configurazione file statici (Logo, CSS, JS)
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Configurazione Login/Logout
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# Configurazione Email
ADMIN_NOTIFY_EMAIL = "antimo.digiovanni@sanvincenzosrl.com"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtps.aruba.it"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'antimo.digiovanni@sanvincenzosrl.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'Unilever_02')  # Cambia con una variabile d'ambiente
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Aggiungi l'indirizzo di default del dominio
DEFAULT_DOMAIN = "cedolini-web.onrender.com"
DEFAULT_PROTOCOL = "https"

# Altri settings
PASSWORD_CHANGE_REDIRECT_URL = "/"